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
