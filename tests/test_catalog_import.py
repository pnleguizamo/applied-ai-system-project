import csv
import importlib
from pathlib import Path

import pytest

from src import catalog_import
from src.recommender import load_songs


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


def make_track(
    spotify_id,
    *,
    name="Test Song",
    artist="Test Artist",
    artist_id="artist-id",
    album="Test Album",
    duration_ms=201500,
    release_date="2024-03-15",
    popularity=84,
    explicit=False,
    is_local=False,
    is_playable=True,
    track_type="track",
    isrc="USRC17607839",
    available_markets=None,
):
    track = {
        "id": spotify_id,
        "type": track_type,
        "name": name,
        "artists": [{"id": artist_id, "name": artist}],
        "album": {"name": album, "release_date": release_date},
        "duration_ms": duration_ms,
        "popularity": popularity,
        "explicit": explicit,
        "is_local": is_local,
        "is_playable": is_playable,
        "external_urls": {"spotify": f"https://open.spotify.com/track/{spotify_id}"},
        "external_ids": {"isrc": isrc},
    }
    if available_markets is not None:
        track["available_markets"] = available_markets
    return track


def read_csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def test_missing_spotify_env_vars_exit_cleanly(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)

    with pytest.raises(SystemExit) as error:
        catalog_import.main(
            [
                "--spotify-playlist-id",
                "playlist-id",
                "--output",
                str(tmp_path / "songs.csv"),
            ]
        )

    captured = capsys.readouterr()
    assert error.value.code == 1
    assert "SPOTIFY_CLIENT_ID" in captured.err
    assert "SPOTIFY_CLIENT_SECRET" in captured.err


def test_import_playlist_paginates_filters_dedupes_and_round_trips(monkeypatch, tmp_path):
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "client-secret")
    get_calls = []

    def fake_post(url, data, auth, timeout):
        assert url == catalog_import.SPOTIFY_TOKEN_URL
        assert data == {"grant_type": "client_credentials"}
        assert auth == ("client-id", "client-secret")
        assert timeout == 20
        return FakeResponse({"access_token": "token"})

    def fake_get(url, headers, params, timeout):
        get_calls.append((url, params))
        assert headers == {"Authorization": "Bearer token"}
        assert timeout == 20
        if len(get_calls) == 1:
            return FakeResponse(
                {
                    "items": [
                        {"track": make_track("track-1", name="First Song", popularity=84)},
                        {"track": make_track("track-1", name="Duplicate Song")},
                        {"track": make_track("episode-1", track_type="episode")},
                        {"track": make_track("local-1", is_local=True)},
                        {"track": make_track(None)},
                    ],
                    "next": "https://api.spotify.com/v1/next-page",
                }
            )
        if len(get_calls) == 2:
            return FakeResponse(
                {
                    "items": [
                        {"track": make_track("unplayable-1", is_playable=False)},
                        {"track": make_track("unavailable-1", available_markets=[])},
                        {"track": None},
                        {
                            "track": make_track(
                                "track-2",
                                name="Second Song",
                                artist="Second Artist",
                                artist_id="second-artist-id",
                                album="Second Album",
                                duration_ms=199999,
                                release_date="bad-date",
                                popularity=55,
                                explicit=True,
                                isrc="GBAYE0601498",
                            )
                        },
                    ],
                    "next": None,
                }
            )
        assert url == catalog_import.SPOTIFY_ARTISTS_URL
        assert params == {"ids": "artist-id,second-artist-id"}
        return FakeResponse(
            {
                "artists": [
                    {"id": "artist-id", "genres": ["dance pop", "electropop"]},
                    {"id": "second-artist-id", "genres": ["classic rock"]},
                ]
            }
        )

    monkeypatch.setattr(catalog_import.requests, "post", fake_post)
    monkeypatch.setattr(catalog_import.requests, "get", fake_get)
    output_path = tmp_path / "songs.spotify.csv"

    exit_code = catalog_import.main(
        [
            "--spotify-playlist-id",
            "playlist-id",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert get_calls == [
        (catalog_import.SPOTIFY_PLAYLIST_ITEMS_URL.format(playlist_id="playlist-id"), {"limit": 100}),
        ("https://api.spotify.com/v1/next-page", None),
        (catalog_import.SPOTIFY_ARTISTS_URL, {"ids": "artist-id,second-artist-id"}),
    ]

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        assert next(reader) == catalog_import.CSV_COLUMNS

    rows = read_csv_rows(output_path)
    assert len(rows) == 2
    assert rows[0]["id"] == "1"
    assert rows[0]["title"] == "First Song"
    assert rows[0]["genre"] == "pop"
    assert rows[0]["artist_genres"] == "dance pop; electropop"
    assert rows[0]["mood"] == "unknown"
    assert rows[0]["energy"] == "0.5"
    assert rows[0]["tempo_bpm"] == "120"
    assert rows[0]["popularity"] == "0.84"
    assert rows[0]["explicit"] == "false"
    assert rows[0]["metadata_source"] == "spotify"
    assert rows[1]["id"] == "2"
    assert rows[1]["genre"] == "rock"
    assert rows[1]["artist_genres"] == "classic rock"
    assert rows[1]["release_year"] == "0"
    assert rows[1]["popularity"] == "0.55"
    assert rows[1]["explicit"] == "true"
    assert rows[1]["spotify_url"] == "https://open.spotify.com/track/track-2"
    assert rows[1]["isrc"] == "GBAYE0601498"

    loaded = load_songs(str(output_path))
    assert len(loaded) == 2
    assert loaded[0]["id"] == 1
    assert loaded[0]["popularity"] == 0.84
    assert loaded[0]["explicit"] is False
    assert loaded[1]["explicit"] is True
    assert loaded[1]["metadata_source"] == "spotify"


def test_write_catalog_csv_creates_parent_directory(tmp_path):
    output_path = tmp_path / "nested" / "songs.csv"

    row_count = catalog_import.write_catalog_csv(
        [{"track": make_track("track-1")}],
        str(output_path),
    )

    assert row_count == 1
    assert output_path.exists()


def test_app_song_path_defaults_to_demo_catalog(monkeypatch):
    monkeypatch.delenv("SONG_PATH", raising=False)

    import src.app as app

    reloaded = importlib.reload(app)

    assert reloaded.SONG_PATH == "data/songs.csv"


def test_app_song_path_can_be_overridden(monkeypatch):
    monkeypatch.setenv("SONG_PATH", "data/generated/songs.spotify.csv")

    import src.app as app

    reloaded = importlib.reload(app)

    assert reloaded.SONG_PATH == "data/generated/songs.spotify.csv"
