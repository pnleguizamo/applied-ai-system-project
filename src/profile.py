import json
import os
import re
import time
from typing import Any, Dict, List, Optional


try:
    from pydantic import BaseModel, Field

    class MusicProfile(BaseModel):
        genre: str
        mood: str
        energy: float = Field(ge=0.0, le=1.0)
        acousticness: float = Field(ge=0.0, le=1.0)
        tempo_bpm: float = Field(ge=40.0, le=220.0)
        duration_sec: int = Field(ge=30, le=600)
        release_year: int = Field(ge=1950, le=2030)
        popularity: float = Field(ge=0.0, le=1.0)
        intent_summary: str
        tags: List[str] = []
        warnings: List[str] = []

except Exception:
    MusicProfile = None


TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
DEFAULT_PROFILE = {
    "genre": "pop",
    "mood": "happy",
    "energy": 0.60,
    "acousticness": 0.40,
    "tempo_bpm": 115.0,
    "duration_sec": 210,
    "release_year": 2022,
    "popularity": 0.65,
}
INTENT_GENRE_HINTS = {
    "study": ["lofi", "ambient", "classical"],
    "focus": ["lofi", "ambient", "synthwave"],
    "workout": ["pop", "rock", "house", "metal"],
    "party": ["house", "reggaeton", "afrobeat", "pop"],
    "sleep": ["ambient", "classical", "lofi"],
    "sad": ["folk", "blues", "chamber pop"],
    "commute": ["synthwave", "pop", "indie pop"],
    "relax": ["jazz", "lofi", "ambient"],
}
LOW_ENERGY_GENRES = {"lofi", "ambient", "classical", "folk", "jazz", "blues", "chamber pop"}
HIGH_ENERGY_INTENTS = {"workout", "party"}


def _tokens(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _catalog_values(songs: List[Dict], field: str) -> list[str]:
    return sorted({str(song[field]) for song in songs if song.get(field)})


def _context_ids(contexts: List[Dict]) -> list[str]:
    return [str(context["id"]) for context in contexts if context.get("id")]


def _clamp(value: Any, minimum: float, maximum: float) -> float:
    return min(max(float(value), minimum), maximum)


def _first_available(candidates: list[str], available: list[str], default: str) -> str:
    for candidate in candidates:
        if candidate in available:
            return candidate
    return default


def _phrase_match(request_text: str, values: list[str]) -> Optional[str]:
    for value in sorted(values, key=len, reverse=True):
        if re.search(rf"(^|\W){re.escape(value)}($|\W)", request_text):
            return value
    return None


def _context_midpoint(contexts: List[Dict], prefix: str, default: float) -> float:
    weighted_total = 0.0
    weight_total = 0.0
    for rank, context in enumerate(contexts):
        min_key = f"target_{prefix}_min"
        max_key = f"target_{prefix}_max"
        if min_key not in context or max_key not in context:
            continue
        weight = max(float(context.get("retrieval_score", 0.0)), 0.0) or 1.0 / (rank + 1)
        weighted_total += ((float(context[min_key]) + float(context[max_key])) / 2) * weight
        weight_total += weight
    if weight_total == 0:
        return default
    return weighted_total / weight_total


def _choose_mood(contexts: List[Dict], catalog_moods: list[str], default: str) -> str:
    for context in contexts:
        for mood in context.get("mood_hints", []):
            if mood in catalog_moods:
                return mood
    return default


def _choose_genre(intent: Optional[str], catalog_genres: list[str], default: str) -> str:
    if intent:
        return _first_available(INTENT_GENRE_HINTS.get(intent, []), catalog_genres, default)
    return default


def _normalize_profile_payload(
    payload: Dict,
    songs: List[Dict],
    contexts: List[Dict],
    *,
    parser_tier: str,
    fallback_reason: Optional[str],
    model_name: Optional[str] = None,
) -> Dict:
    catalog_genres = _catalog_values(songs, "genre")
    catalog_moods = _catalog_values(songs, "mood")

    genre = str(payload.get("genre", "")).strip().lower()
    mood = str(payload.get("mood", "")).strip().lower()
    if genre not in catalog_genres:
        raise ValueError(f"unknown genre: {genre}")
    if mood not in catalog_moods:
        raise ValueError(f"unknown mood: {mood}")

    profile = {
        "genre": genre,
        "mood": mood,
        "energy": _clamp(payload.get("energy", DEFAULT_PROFILE["energy"]), 0.0, 1.0),
        "acousticness": _clamp(payload.get("acousticness", DEFAULT_PROFILE["acousticness"]), 0.0, 1.0),
        "tempo_bpm": _clamp(payload.get("tempo_bpm", DEFAULT_PROFILE["tempo_bpm"]), 40.0, 220.0),
        "duration_sec": int(_clamp(payload.get("duration_sec", DEFAULT_PROFILE["duration_sec"]), 30, 600)),
        "release_year": int(_clamp(payload.get("release_year", DEFAULT_PROFILE["release_year"]), 1950, 2030)),
        "popularity": _clamp(payload.get("popularity", DEFAULT_PROFILE["popularity"]), 0.0, 1.0),
        "intent_summary": str(payload.get("intent_summary") or "Playlist request"),
        "tags": list(payload.get("tags") or []),
        "warnings": list(payload.get("warnings") or []),
        "parser_tier": parser_tier,
        "parser_fallback_reason": fallback_reason,
        "model_name": model_name,
        "latency_ms": int(payload.get("latency_ms", 0) or 0),
    }

    if MusicProfile is not None:
        validated = MusicProfile(**{key: profile[key] for key in MusicProfile.model_fields})
        profile.update(validated.model_dump())

    return profile


def _fallback_profile(
    user_request: str,
    retrieved_contexts: List[Dict],
    songs: List[Dict],
    fallback_reason: str,
) -> Dict:
    request_text = user_request.lower()
    request_tokens = _tokens(user_request)
    token_counts = {token: request_tokens.count(token) for token in set(request_tokens)}
    catalog_genres = _catalog_values(songs, "genre")
    catalog_moods = _catalog_values(songs, "mood")
    context_ids = _context_ids(retrieved_contexts)

    genre = _phrase_match(request_text, catalog_genres)
    mood = _phrase_match(request_text, catalog_moods)
    intent = next((context_id for context_id in context_ids if context_id in request_tokens), None)
    if intent is None and retrieved_contexts and retrieved_contexts[0].get("retrieval_score", 0) > 0:
        intent = str(retrieved_contexts[0].get("id"))

    warnings: list[str] = []
    tags = [intent] if intent else []
    direct_hits = bool(genre or mood or intent)

    default_genre = DEFAULT_PROFILE["genre"] if DEFAULT_PROFILE["genre"] in catalog_genres else catalog_genres[0]
    default_mood = DEFAULT_PROFILE["mood"] if DEFAULT_PROFILE["mood"] in catalog_moods else catalog_moods[0]

    if not direct_hits:
        warnings.append("vague request: no catalog genre, mood, or supported intent was detected")

    if genre is None:
        genre = _choose_genre(intent, catalog_genres, default_genre)
    if mood is None:
        mood = _choose_mood(retrieved_contexts, catalog_moods, default_mood)

    if genre in LOW_ENERGY_GENRES and intent in HIGH_ENERGY_INTENTS:
        genre_signal = token_counts.get(genre.split()[0], 0)
        intent_signal = token_counts.get(intent, 0)
        warnings.append(
            f"contradiction: {genre} usually points lower energy while {intent} points higher energy"
        )
        if intent_signal > genre_signal:
            genre = _choose_genre(intent, catalog_genres, genre)

    energy = _context_midpoint(retrieved_contexts, "energy", DEFAULT_PROFILE["energy"])
    tempo_bpm = _context_midpoint(retrieved_contexts, "tempo", DEFAULT_PROFILE["tempo_bpm"])
    acousticness = _context_midpoint(retrieved_contexts, "acousticness", DEFAULT_PROFILE["acousticness"])

    payload = {
        "genre": genre,
        "mood": mood,
        "energy": energy,
        "acousticness": acousticness,
        "tempo_bpm": tempo_bpm,
        "duration_sec": DEFAULT_PROFILE["duration_sec"],
        "release_year": DEFAULT_PROFILE["release_year"],
        "popularity": DEFAULT_PROFILE["popularity"],
        "intent_summary": f"Interpreted as {intent or 'general listening'}",
        "tags": tags,
        "warnings": warnings,
    }
    return _normalize_profile_payload(
        payload,
        songs,
        retrieved_contexts,
        parser_tier="fallback",
        fallback_reason=fallback_reason,
    )


def _extract_response_payload(response: Any) -> Dict:
    if isinstance(response, dict):
        return response
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed
    text = getattr(response, "text", None)
    if text:
        return json.loads(text)
    if hasattr(response, "model_dump"):
        return response.model_dump()
    raise ValueError("Gemini response did not contain a parseable profile")


def _call_gemini(user_request: str, retrieved_contexts: List[Dict], model_client=None) -> tuple[Dict, str, int]:
    model_name = "gemini-2.0-flash"
    prompt = {
        "task": "Turn this listening request into a catalog-compatible music profile.",
        "request": user_request,
        "retrieved_contexts": retrieved_contexts,
        "required_fields": list(DEFAULT_PROFILE.keys()) + ["intent_summary", "tags", "warnings"],
    }
    started = time.perf_counter()

    if model_client is not None:
        if hasattr(model_client, "generate_profile"):
            response = model_client.generate_profile(prompt)
        elif hasattr(model_client, "models"):
            response = model_client.models.generate_content(
                model=model_name,
                contents=json.dumps(prompt),
                config={"response_mime_type": "application/json", "response_schema": MusicProfile},
            )
        else:
            response = model_client(user_request, retrieved_contexts)
    else:
        from google import genai

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=model_name,
            contents=json.dumps(prompt),
            config={"response_mime_type": "application/json", "response_schema": MusicProfile},
        )

    latency_ms = int((time.perf_counter() - started) * 1000)
    return _extract_response_payload(response), model_name, latency_ms


def build_profile_from_request(
    user_request: str,
    retrieved_contexts: List[Dict],
    *,
    songs: List[Dict],
    force_fallback: bool = False,
    model_client=None,
) -> Dict:
    """Build a validated scorer-compatible profile from a natural-language request."""
    if force_fallback:
        return _fallback_profile(user_request, retrieved_contexts, songs, "forced fallback parser")

    if not os.environ.get("GEMINI_API_KEY") and model_client is None:
        return _fallback_profile(user_request, retrieved_contexts, songs, "missing GEMINI_API_KEY")

    try:
        payload, model_name, latency_ms = _call_gemini(user_request, retrieved_contexts, model_client)
        payload["latency_ms"] = latency_ms
        return _normalize_profile_payload(
            payload,
            songs,
            retrieved_contexts,
            parser_tier="gemini",
            fallback_reason=None,
            model_name=model_name,
        )
    except Exception as exc:
        return _fallback_profile(user_request, retrieved_contexts, songs, f"gemini fallback: {exc}")
