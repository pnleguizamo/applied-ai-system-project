"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.
"""

from typing import Dict

from src.recommender import load_songs, recommend_songs


def print_recommendations(profile_name: str, user_prefs: Dict, songs: list[Dict], k: int = 5) -> None:
    """Print the top recommendations for one named user profile."""
    recommendations = recommend_songs(user_prefs, songs, k=k)

    print(f"\n=== {profile_name} ===\n")
    for song, score, reasons in recommendations:
        reason_text = ", ".join(reasons) if reasons else "closest overall match"
        print(f"{song['title']} by {song['artist']}")
        print(f"Score: {score:.2f}")
        print(f"Reasons: {reason_text}")
        print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    print(f"Loaded songs: {len(songs)}")

    test_profiles = {
        "High-Energy Pop": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.88,
            "acousticness": 0.15,
            "tempo_bpm": 126,
            "duration_sec": 200,
            "release_year": 2023,
            "popularity": 0.85,
        },
        "Chill Lofi": {
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.38,
            "acousticness": 0.82,
            "tempo_bpm": 78,
            "duration_sec": 205,
            "release_year": 2021,
            "popularity": 0.55,
        },
        "Deep Intense Rock": {
            "genre": "rock",
            "mood": "intense",
            "energy": 0.92,
            "acousticness": 0.10,
            "tempo_bpm": 150,
            "duration_sec": 225,
            "release_year": 2018,
            "popularity": 0.65,
        },
        "Conflicting Preferences": {
            "genre": "lofi",
            "mood": "intense",
            "energy": 0.90,
            "acousticness": 0.85,
            "tempo_bpm": 82,
            "duration_sec": 210,
            "release_year": 2023,
            "popularity": 0.60,
        },
        "Unsupported Mood Edge Case": {
            "genre": "pop",
            "mood": "sad",
            "energy": 0.80,
            "acousticness": 0.20,
            "tempo_bpm": 120,
            "duration_sec": 200,
            "release_year": 2022,
            "popularity": 0.80,
        },
        "Impossible Hybrid": {
            "genre": "classical",
            "mood": "euphoric",
            "energy": 0.98,
            "acousticness": 0.98,
            "tempo_bpm": 170,
            "duration_sec": 300,
            "release_year": 2024,
            "popularity": 0.95,
        },
    }

    for profile_name, user_prefs in test_profiles.items():
        print_recommendations(profile_name, user_prefs, songs, k=3)


if __name__ == "__main__":
    main()
