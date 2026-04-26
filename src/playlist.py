from typing import Dict, List, Literal, Tuple

from src.audit import audit_recommendations
from src.profile import build_profile_from_request
from src.rag import retrieve_contexts
from src.recommender import recommend_songs


Recommendation = Tuple[Dict, float, List[str]]


def _filter_explicit(songs: List[Dict], allow_explicit: bool) -> List[Dict]:
    if allow_explicit:
        return list(songs)
    return [song for song in songs if not song.get("explicit", False)]


def _diversify_recommendations(ranked: List[Recommendation], length: int) -> List[Recommendation]:
    selected: list[Recommendation] = []
    remaining = list(ranked)
    used_pairs = set()

    while remaining and len(selected) < length:
        anchor_score = remaining[0][1]
        bucket = [item for item in remaining if anchor_score - item[1] <= 0.5]
        choice = next(
            (
                item
                for item in bucket
                if (item[0].get("artist"), item[0].get("genre")) not in used_pairs
            ),
            bucket[0],
        )
        selected.append(choice)
        used_pairs.add((choice[0].get("artist"), choice[0].get("genre")))
        remaining.remove(choice)

    return selected


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _stage_profile(base_profile: Dict, label: str) -> Dict:
    staged = dict(base_profile)
    staged["stage"] = label
    if label == "warmup":
        staged["energy"] = _clamp(base_profile["energy"] - 0.25, 0.0, 1.0)
        staged["tempo_bpm"] = _clamp(base_profile["tempo_bpm"] - 20, 40, 220)
        staged["acousticness"] = _clamp(base_profile["acousticness"] + 0.20, 0.0, 1.0)
    elif label == "peak":
        staged["energy"] = _clamp(base_profile["energy"] + 0.25, 0.0, 1.0)
        staged["tempo_bpm"] = _clamp(base_profile["tempo_bpm"] + 20, 40, 220)
        staged["acousticness"] = _clamp(base_profile["acousticness"] - 0.20, 0.0, 1.0)
    return staged


def _arc_recommendations(profile: Dict, songs: List[Dict], length: int) -> tuple[list[Dict], list[Recommendation], list[Dict]]:
    first = length // 3
    stage_lengths = [first, length - 2 * first, first]
    labels = ["warmup", "middle", "peak"]
    staged_profiles = [_stage_profile(profile, label) for label in labels]
    remaining_songs = list(songs)
    flat_recommendations: list[Recommendation] = []
    stages: list[Dict] = []

    for label, stage_length, staged_profile in zip(labels, stage_lengths, staged_profiles):
        stage_recs = recommend_songs(staged_profile, remaining_songs, k=stage_length)
        selected_ids = {song["id"] for song, _, _ in stage_recs}
        remaining_songs = [song for song in remaining_songs if song.get("id") not in selected_ids]
        flat_recommendations.extend(stage_recs)
        stages.append({"stage": label, "profile": staged_profile, "recommendations": stage_recs})

    return staged_profiles, flat_recommendations, stages


def _explanations(recommendations: List[Recommendation]) -> list[str]:
    return [
        ", ".join(reasons) if reasons else "closest overall match"
        for _, _, reasons in recommendations
    ]


def generate_playlist(
    user_request: str,
    songs: List[Dict],
    contexts: List[Dict],
    *,
    length: int,
    mode: Literal["close_match", "variety", "arc"],
    allow_explicit: bool,
    force_fallback: bool = False,
    model_client=None,
) -> Dict:
    """Generate a recommended playlist from a natural-language request."""
    if mode not in {"close_match", "variety", "arc"}:
        raise ValueError(f"unsupported playlist mode: {mode}")

    playlist_length = max(int(length), 1)
    filtered_songs = _filter_explicit(songs, allow_explicit)
    retrieved_contexts = retrieve_contexts(user_request, contexts, k=2)
    profile = build_profile_from_request(
        user_request,
        retrieved_contexts,
        songs=songs,
        force_fallback=force_fallback,
        model_client=model_client,
    )

    staged_profiles = None
    stages = None
    if mode == "close_match":
        recommendations = recommend_songs(profile, filtered_songs, k=playlist_length)
    elif mode == "variety":
        ranked = recommend_songs(profile, filtered_songs, k=len(filtered_songs))
        recommendations = _diversify_recommendations(ranked, playlist_length)
    else:
        staged_profiles, recommendations, stages = _arc_recommendations(
            profile,
            filtered_songs,
            playlist_length,
        )

    audit = audit_recommendations(
        user_request,
        profile,
        recommendations,
        filtered_songs,
        original_song_count=len(songs),
    )

    result = {
        "profile": profile,
        "retrieved_contexts": retrieved_contexts,
        "recommendations": recommendations,
        "explanations": _explanations(recommendations),
        "audit": audit,
        "parser_tier": profile.get("parser_tier"),
        "parser_fallback_reason": profile.get("parser_fallback_reason"),
    }
    if staged_profiles is not None:
        result["staged_profiles"] = staged_profiles
        result["stages"] = stages
    return result
