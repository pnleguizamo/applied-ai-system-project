"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.
"""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")

    # Starter example profile for assignment verification.
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    print(f"Loaded songs: {len(songs)}")

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\nTop recommendations:\n")
    for song, score, reasons in recommendations:
        reason_text = ", ".join(reasons) if reasons else "closest overall match"
        print(f"{song['title']} by {song['artist']}")
        print(f"Score: {score:.2f}")
        print(f"Reasons: {reason_text}")
        print()


if __name__ == "__main__":
    main()
