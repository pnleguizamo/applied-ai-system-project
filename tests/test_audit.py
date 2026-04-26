from src.audit import audit_recommendations
from src.recommender import recommend_songs


def sample_songs():
    return [
        {
            "id": 1,
            "title": "A",
            "artist": "One",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "tempo_bpm": 120,
            "valence": 0.8,
            "danceability": 0.8,
            "acousticness": 0.2,
            "duration_sec": 200,
            "release_year": 2024,
            "popularity": 0.9,
        },
        {
            "id": 2,
            "title": "B",
            "artist": "Two",
            "genre": "rock",
            "mood": "intense",
            "energy": 0.9,
            "tempo_bpm": 150,
            "valence": 0.5,
            "danceability": 0.6,
            "acousticness": 0.1,
            "duration_sec": 220,
            "release_year": 2020,
            "popularity": 0.7,
        },
    ]


def test_strong_exact_match_has_good_confidence():
    profile = {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.8,
        "acousticness": 0.2,
        "tempo_bpm": 120,
        "duration_sec": 200,
        "release_year": 2024,
        "popularity": 0.9,
        "warnings": [],
    }
    recommendations = recommend_songs(profile, sample_songs(), k=2)

    audit = audit_recommendations("happy pop", profile, recommendations, sample_songs())

    assert audit["confidence"] >= 0.7


def test_unsupported_genre_has_low_confidence_and_warning():
    profile = {
        "genre": "opera",
        "mood": "furious",
        "energy": 0.8,
        "acousticness": 0.2,
        "tempo_bpm": 120,
        "warnings": [],
    }
    recommendations = recommend_songs(profile, sample_songs(), k=2)

    audit = audit_recommendations("opera", profile, recommendations, sample_songs())

    assert audit["confidence"] <= 0.5
    assert any("does not contain" in warning for warning in audit["warnings"])


def test_tiny_candidate_pool_warns():
    profile = {"genre": "pop", "mood": "happy", "energy": 0.8, "warnings": []}
    recommendations = recommend_songs(profile, sample_songs(), k=2)

    audit = audit_recommendations("happy pop", profile, recommendations, sample_songs())

    assert any("very small candidate pool" in warning for warning in audit["warnings"])


def test_energy_only_reasons_warn_about_genre_gap():
    songs = sample_songs()
    profile = {
        "genre": "classical",
        "mood": "serene",
        "energy": 0.8,
        "acousticness": 0.2,
        "tempo_bpm": 120,
        "warnings": [],
    }
    recommendations = recommend_songs(profile, songs, k=2)

    audit = audit_recommendations("energy match", profile, recommendations, songs)

    assert any("energy and tempo" in warning for warning in audit["warnings"])
