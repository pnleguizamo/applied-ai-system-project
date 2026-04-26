from src.playlist import generate_playlist
from src.rag import load_context_docs
from src.recommender import load_songs


def songs():
    return load_songs("data/songs.csv")


def contexts():
    return load_context_docs("data/context_docs")


def test_close_match_sorted_and_unique():
    result = generate_playlist(
        "upbeat workout music",
        songs(),
        contexts(),
        length=5,
        mode="close_match",
        allow_explicit=True,
        force_fallback=True,
    )

    scores = [score for _, score, _ in result["recommendations"]]
    ids = [song["id"] for song, _, _ in result["recommendations"]]
    assert scores == sorted(scores, reverse=True)
    assert len(ids) == len(set(ids))


def test_explicit_filter_removes_explicit_rows():
    catalog = songs()
    catalog[0] = dict(catalog[0], explicit=True)

    result = generate_playlist(
        "happy pop music",
        catalog,
        contexts(),
        length=5,
        mode="close_match",
        allow_explicit=False,
        force_fallback=True,
    )

    assert all(not song.get("explicit") for song, _, _ in result["recommendations"])


def test_variety_mode_diversifies_near_ties():
    result = generate_playlist(
        "quiet study music",
        songs(),
        contexts(),
        length=5,
        mode="variety",
        allow_explicit=True,
        force_fallback=True,
    )

    pairs = [(song["artist"], song["genre"]) for song, _, _ in result["recommendations"]]
    assert len(set(pairs)) >= 3


def test_arc_mode_has_three_stages_with_unique_songs():
    result = generate_playlist(
        "upbeat workout music",
        songs(),
        contexts(),
        length=9,
        mode="arc",
        allow_explicit=True,
        force_fallback=True,
    )

    energies = [profile["energy"] for profile in result["staged_profiles"]]
    ids = [song["id"] for song, _, _ in result["recommendations"]]
    assert len(result["staged_profiles"]) == 3
    assert energies[0] < energies[1] < energies[2]
    assert len(ids) == len(set(ids))
