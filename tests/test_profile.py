from pathlib import Path

from src.profile import build_profile_from_request
from src.rag import load_context_docs, retrieve_contexts
from src.recommender import load_songs


def songs():
    return load_songs("data/songs.csv")


def contexts_for(request):
    docs = load_context_docs("data/context_docs")
    return retrieve_contexts(request, docs, k=2)


def test_workout_profile_uses_high_energy_targets(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    request = "upbeat workout music"

    profile = build_profile_from_request(request, contexts_for(request), songs=songs())

    assert profile["parser_tier"] == "fallback"
    assert profile["energy"] >= 0.75
    assert profile["tempo_bpm"] >= 115


def test_study_profile_uses_low_energy_high_acousticness(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    request = "quiet study music"

    profile = build_profile_from_request(request, contexts_for(request), songs=songs())

    assert profile["energy"] <= 0.55
    assert profile["acousticness"] >= 0.60


def test_vague_request_gets_warning(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    request = "asdfgh nonsense"

    profile = build_profile_from_request(request, contexts_for(request), songs=songs())

    assert any("vague request" in warning for warning in profile["warnings"])
    assert profile["parser_tier"] == "fallback"


def test_lofi_workout_gets_contradiction_warning(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    request = "lofi workout"

    profile = build_profile_from_request(request, contexts_for(request), songs=songs())

    assert profile["genre"] == "lofi"
    assert any("contradiction" in warning for warning in profile["warnings"])


def test_missing_explicit_column_defaults_false(tmp_path: Path):
    csv_path = tmp_path / "songs.csv"
    csv_path.write_text(
        "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness,duration_sec,release_year,popularity\n"
        "1,Test,Artist,pop,happy,0.8,120,0.7,0.8,0.2,200,2024,0.9\n",
        encoding="utf-8",
    )

    loaded = load_songs(str(csv_path))

    assert loaded[0]["explicit"] is False
