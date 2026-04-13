import csv
from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple


NUMERIC_INT_FIELDS = {"id", "duration_sec", "release_year"}
NUMERIC_FLOAT_FIELDS = {
    "energy",
    "tempo_bpm",
    "valence",
    "danceability",
    "acousticness",
    "popularity",
}

NUMERIC_SCORING_CONFIG = {
    "energy": (2.0, 1.0, "energy close to target"),
    "acousticness": (1.0, 1.0, "acousticness close to target"),
    "tempo_bpm": (1.0, 80.0, "tempo close to target"),
    "duration_sec": (0.75, 180.0, "duration close to target"),
    "release_year": (0.75, 15.0, "release year close to target"),
    "popularity": (0.5, 1.0, "popularity close to target"),
}


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """

    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    duration_sec: int = 0
    release_year: int = 0
    popularity: float = 0.0


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """

    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


def _normalize_user_prefs(user_prefs: Dict) -> Dict:
    """Normalize user preference keys into one shared scoring dictionary."""
    normalized = {
        "genre": user_prefs.get("genre", user_prefs.get("favorite_genre")),
        "mood": user_prefs.get("mood", user_prefs.get("favorite_mood")),
        "energy": user_prefs.get("energy", user_prefs.get("target_energy")),
        "acousticness": user_prefs.get(
            "acousticness",
            user_prefs.get("target_acousticness"),
        ),
        "tempo_bpm": user_prefs.get(
            "tempo_bpm",
            user_prefs.get("target_tempo_bpm"),
        ),
        "duration_sec": user_prefs.get(
            "duration_sec",
            user_prefs.get("target_duration_sec"),
        ),
        "release_year": user_prefs.get(
            "release_year",
            user_prefs.get("target_release_year"),
        ),
        "popularity": user_prefs.get(
            "popularity",
            user_prefs.get("target_popularity"),
        ),
    }

    if normalized["acousticness"] is None and "likes_acoustic" in user_prefs:
        normalized["acousticness"] = 0.8 if user_prefs["likes_acoustic"] else 0.2

    return normalized


def _score_numeric_feature(song_value: float, target_value: float, weight: float, range_width: float) -> float:
    """Return a weighted closeness score for one numeric feature."""
    normalized_score = max(0.0, 1 - abs(song_value - target_value) / range_width)
    return weight * normalized_score


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against user preferences and collect match reasons."""
    normalized_prefs = _normalize_user_prefs(user_prefs)
    score = 0.0
    reasons: List[str] = []

    if normalized_prefs.get("genre") and song.get("genre") == normalized_prefs["genre"]:
        score += 3.0
        reasons.append("genre match (+3.0)")

    if normalized_prefs.get("mood") and song.get("mood") == normalized_prefs["mood"]:
        score += 2.0
        reasons.append("mood match (+2.0)")

    for feature, (weight, range_width, label) in NUMERIC_SCORING_CONFIG.items():
        target_value = normalized_prefs.get(feature)
        song_value = song.get(feature)
        if target_value is None or song_value is None:
            continue

        contribution = _score_numeric_feature(
            float(song_value),
            float(target_value),
            weight,
            range_width,
        )
        score += contribution
        if contribution >= 0.2:
            reasons.append(f"{label} (+{contribution:.1f})")

    return score, reasons


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _user_to_dict(self, user: UserProfile) -> Dict:
        return {
            "favorite_genre": user.favorite_genre,
            "favorite_mood": user.favorite_mood,
            "target_energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        }

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        ranked_songs = sorted(
            self.songs,
            key=lambda song: (
                -score_song(self._user_to_dict(user), asdict(song))[0],
                song.title,
            ),
        )
        return ranked_songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        _, reasons = score_song(self._user_to_dict(user), asdict(song))
        if reasons:
            return ", ".join(reasons)
        return "This song is one of the closest overall matches to your profile."


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and parse numeric columns."""
    songs: List[Dict] = []

    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            parsed_row: Dict = {}
            for key, value in row.items():
                if key in NUMERIC_INT_FIELDS:
                    parsed_row[key] = int(value)
                elif key in NUMERIC_FLOAT_FIELDS:
                    parsed_row[key] = float(value)
                else:
                    parsed_row[key] = value
            songs.append(parsed_row)

    return songs


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, List[str]]]:
    """Rank songs by score and return the top recommendations with reasons."""
    scored_songs = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored_songs.append((song, score, reasons))

    ranked_songs = sorted(
        scored_songs,
        key=lambda item: (-item[1], item[0]["title"]),
    )
    return ranked_songs[:k]
