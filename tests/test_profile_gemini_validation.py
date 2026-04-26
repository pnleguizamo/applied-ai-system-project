import json

from src.profile import build_profile_from_request
from src.rag import load_context_docs, retrieve_contexts
from src.recommender import load_songs


class BadGeminiClient:
    def generate_profile(self, prompt):
        return {
            "genre": "space polka",
            "mood": "happy",
            "energy": 0.8,
            "acousticness": 0.2,
            "tempo_bpm": 120,
            "duration_sec": 200,
            "release_year": 2024,
            "popularity": 0.8,
            "intent_summary": "bad enum",
            "tags": [],
            "warnings": [],
        }


class RecordingGeminiClient:
    def __init__(self):
        self.models = self
        self.model_name = None
        self.contents = None

    def generate_content(self, *, model, contents, config):
        self.model_name = model
        self.contents = contents
        return {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.8,
            "acousticness": 0.2,
            "tempo_bpm": 120,
            "duration_sec": 200,
            "release_year": 2024,
            "popularity": 0.8,
            "intent_summary": "valid profile",
            "tags": [],
            "warnings": [],
        }


class CompoundGenreGeminiClient:
    def generate_profile(self, prompt):
        return {
            "genre": "dance pop",
            "mood": "happy",
            "energy": 0.8,
            "acousticness": 0.2,
            "tempo_bpm": 120,
            "duration_sec": 200,
            "release_year": 2024,
            "popularity": 0.8,
            "intent_summary": "valid profile with a compound genre",
            "tags": [],
            "warnings": [],
        }


class UnsupportedMoodGeminiClient:
    def generate_profile(self, prompt):
        return {
            "genre": "pop",
            "mood": "chill",
            "energy": 0.35,
            "acousticness": 0.8,
            "tempo_bpm": 90,
            "duration_sec": 200,
            "release_year": 2024,
            "popularity": 0.8,
            "intent_summary": "valid profile with a placeholder mood catalog",
            "tags": [],
            "warnings": [],
        }


def test_bad_gemini_enum_falls_back(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    request = "upbeat workout music"
    songs = load_songs("data/songs.csv")
    contexts = retrieve_contexts(request, load_context_docs("data/context_docs"), k=2)

    profile = build_profile_from_request(
        request,
        contexts,
        songs=songs,
        model_client=BadGeminiClient(),
    )

    assert profile["parser_tier"] == "fallback"
    assert "unknown genre" in profile["parser_fallback_reason"]


def test_gemini_model_can_be_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    request = "upbeat workout music"
    songs = load_songs("data/songs.csv")
    contexts = retrieve_contexts(request, load_context_docs("data/context_docs"), k=2)
    client = RecordingGeminiClient()

    profile = build_profile_from_request(
        request,
        contexts,
        songs=songs,
        model_client=client,
    )

    assert client.model_name == "gemini-2.5-flash"
    assert "pop" in json.loads(client.contents)["allowed_genres"]
    assert "happy" in json.loads(client.contents)["allowed_moods"]
    assert profile["model_name"] == "gemini-2.5-flash"
    assert profile["parser_tier"] == "gemini"


def test_compound_gemini_genre_maps_to_catalog_value(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    request = "upbeat dance pop"
    songs = load_songs("data/songs.csv")
    contexts = retrieve_contexts(request, load_context_docs("data/context_docs"), k=2)

    profile = build_profile_from_request(
        request,
        contexts,
        songs=songs,
        model_client=CompoundGenreGeminiClient(),
    )

    assert profile["parser_tier"] == "gemini"
    assert profile["genre"] == "pop"
    assert any("dance pop" in warning for warning in profile["warnings"])


def test_unknown_only_catalog_mood_maps_to_unknown(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    request = "chill music"
    songs = [
        {
            "id": 1,
            "title": "Placeholder Mood",
            "artist": "Artist",
            "genre": "pop",
            "mood": "unknown",
            "energy": 0.5,
            "tempo_bpm": 120.0,
            "valence": 0.5,
            "danceability": 0.5,
            "acousticness": 0.5,
            "duration_sec": 200,
            "release_year": 2024,
            "popularity": 0.7,
            "explicit": False,
        }
    ]

    profile = build_profile_from_request(
        request,
        [],
        songs=songs,
        model_client=UnsupportedMoodGeminiClient(),
    )

    assert profile["parser_tier"] == "gemini"
    assert profile["mood"] == "unknown"
    assert any("chill" in warning for warning in profile["warnings"])
