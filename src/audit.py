from typing import Dict, List, Optional, Tuple

from src.recommender import NUMERIC_SCORING_CONFIG


Recommendation = Tuple[Dict, float, List[str]]


def _max_possible_score() -> float:
    categorical_score = 3.0 + 2.0
    numeric_score = sum(weight for weight, _, _ in NUMERIC_SCORING_CONFIG.values())
    return categorical_score + numeric_score


def _clamp01(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _reason_mentions_top_match(recommendations: List[Recommendation]) -> bool:
    for _, _, reasons in recommendations[:3]:
        reason_text = " ".join(reasons).lower()
        if "genre match" in reason_text or "mood match" in reason_text:
            return True
    return False


def audit_recommendations(
    user_request: str,
    profile: Dict,
    recommendations: List[Recommendation],
    songs: List[Dict],
    *,
    original_song_count: Optional[int] = None,
) -> Dict:
    """Heuristic reliability audit for one generated playlist."""
    warnings: list[str] = []
    strengths: list[str] = []
    profile_warnings = list(profile.get("warnings") or [])

    top_score = recommendations[0][1] if recommendations else 0.0
    top_score_strength = _clamp01(top_score / _max_possible_score())

    genre = profile.get("genre")
    mood = profile.get("mood")
    exact_genre = any(song.get("genre") == genre for song in songs)
    exact_mood = any(song.get("mood") == mood for song in songs)
    exact_pair = any(song.get("genre") == genre and song.get("mood") == mood for song in songs)
    if exact_pair:
        exact_match_availability = 1.0
        strengths.append("catalog contains at least one exact genre and mood match")
    elif exact_genre or exact_mood:
        exact_match_availability = 0.5
        warnings.append("catalog only partially supports the requested genre or mood")
    else:
        exact_match_availability = 0.0
        warnings.append("catalog does not contain the requested genre or mood")

    candidate_count = _clamp01(len(songs) / 20)
    if len(songs) <= 3:
        warnings.append("catalog limit: very small candidate pool")
    elif len(songs) >= 10:
        strengths.append("catalog has enough candidates for ranking")

    confidence = (top_score_strength + exact_match_availability + candidate_count) / 3

    if any("vague request" in warning.lower() for warning in profile_warnings):
        confidence -= 0.15
        warnings.append("request was vague, so the profile used defaults")
    if any("contradiction" in warning.lower() for warning in profile_warnings):
        confidence -= 0.15
        warnings.append("request contained conflicting listening signals")
    if original_song_count and original_song_count > 0:
        removed_ratio = (original_song_count - len(songs)) / original_song_count
        if removed_ratio > 0.5:
            confidence -= 0.10
            warnings.append("explicit filtering removed more than half the catalog")
    if len(recommendations) >= 2 and recommendations[0][1] - recommendations[-1][1] < 1.0:
        confidence -= 0.10
        warnings.append("top recommendations are tightly clustered in score")
    if recommendations and not _reason_mentions_top_match(recommendations):
        confidence -= 0.10
        warnings.append("recommendations rely mostly on energy and tempo, not genre or mood")

    if top_score_strength >= 0.65:
        strengths.append("top recommendation scored strongly")

    confidence = round(_clamp01(confidence), 2)
    warning_text = "; ".join(warnings) if warnings else "no major reliability warnings"
    audit_summary = f"Confidence {confidence:.2f}: {warning_text}."

    return {
        "confidence": confidence,
        "warnings": warnings,
        "strengths": strengths,
        "audit_summary": audit_summary,
    }
