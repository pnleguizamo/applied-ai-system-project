import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests


SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_PLAYLIST_ITEMS_URL = "https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
SPOTIFY_ARTISTS_URL = "https://api.spotify.com/v1/artists"
CSV_COLUMNS = [
    "id",
    "title",
    "artist",
    "album",
    "genre",
    "artist_genres",
    "mood",
    "energy",
    "tempo_bpm",
    "valence",
    "danceability",
    "acousticness",
    "duration_sec",
    "release_year",
    "popularity",
    "explicit",
    "spotify_id",
    "spotify_url",
    "isrc",
    "metadata_source",
]
ARTIST_BATCH_SIZE = 50
MAX_REQUEST_ATTEMPTS = 3
GENRE_KEYWORD_MAP = [
    ("hip hop", ("hip hop", "rap", "trap", "drill")),
    ("r&b", ("r&b", "soul", "neo soul")),
    ("reggaeton", ("reggaeton", "urbano", "latin hip hop", "dembow")),
    ("afrobeat", ("afrobeat", "afrobeats", "afropop", "azonto")),
    ("indie pop", ("indie pop", "indietronica")),
    ("chamber pop", ("chamber pop", "baroque pop")),
    ("pop", ("pop",)),
    ("synthwave", ("synthwave", "retrowave", "vaporwave")),
    ("ambient", ("ambient", "drone", "new age")),
    ("classical", ("classical", "orchestra", "orchestral", "opera", "baroque")),
    ("lofi", ("lo-fi", "lofi")),
    ("house", ("house", "edm", "electro", "techno", "trance", "dance")),
    ("metal", ("metal", "hardcore", "deathcore", "metalcore")),
    ("rock", ("rock", "punk", "grunge", "alternative")),
    ("folk", ("folk", "singer-songwriter", "americana", "bluegrass", "country")),
    ("jazz", ("jazz", "bebop", "swing")),
    ("blues", ("blues",)),
]


class CatalogImportError(Exception):
    """Raised when Spotify catalog import cannot complete."""


def get_access_token(client_id: str, client_secret: str) -> str:
    """Request a Spotify client-credentials access token."""
    try:
        response = requests.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            timeout=20,
        )
    except requests.RequestException as error:
        raise CatalogImportError(f"Spotify authentication failed: {error}") from error
    _raise_for_status(response, "Spotify authentication failed")
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise CatalogImportError("Spotify authentication did not return an access token.")
    return str(token)


def fetch_playlist_tracks(playlist_id: str, token: str) -> List[Dict]:
    """Fetch all playlist item payloads from a public Spotify playlist."""
    headers = {"Authorization": f"Bearer {token}"}
    url: Optional[str] = SPOTIFY_PLAYLIST_ITEMS_URL.format(playlist_id=playlist_id)
    params: Optional[Dict[str, object]] = {"limit": 100}
    items: List[Dict] = []

    while url:
        try:
            response = _get_with_retries(url, headers=headers, params=params)
        except requests.RequestException as error:
            raise CatalogImportError(f"Spotify playlist fetch failed: {error}") from error
        _raise_for_status(response, "Spotify playlist fetch failed")
        payload = response.json()
        items.extend(payload.get("items", []))
        url = payload.get("next")
        params = None

    return items


def fetch_artist_genres(artist_ids: Iterable[str], token: str) -> Dict[str, List[str]]:
    """Fetch Spotify artist genre labels keyed by artist ID."""
    unique_ids = sorted({artist_id for artist_id in artist_ids if artist_id})
    headers = {"Authorization": f"Bearer {token}"}
    genres_by_artist: Dict[str, List[str]] = {}

    for start in range(0, len(unique_ids), ARTIST_BATCH_SIZE):
        batch = unique_ids[start : start + ARTIST_BATCH_SIZE]
        try:
            response = _get_with_retries(
                SPOTIFY_ARTISTS_URL,
                headers=headers,
                params={"ids": ",".join(batch)},
            )
        except requests.RequestException as error:
            raise CatalogImportError(f"Spotify artist fetch failed: {error}") from error
        _raise_for_status(response, "Spotify artist fetch failed")
        payload = response.json()
        for artist in payload.get("artists", []):
            if not isinstance(artist, dict) or not artist.get("id"):
                continue
            genres_by_artist[str(artist["id"])] = [
                str(genre).strip().lower()
                for genre in artist.get("genres", [])
                if str(genre).strip()
            ]

    return genres_by_artist


def write_catalog_csv(
    playlist_items: Iterable[Dict],
    output_path: str,
    artist_genres: Optional[Dict[str, List[str]]] = None,
) -> int:
    """Write valid Spotify track items to a load_songs-compatible CSV."""
    rows = _catalog_rows(playlist_items, artist_genres or {})
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


def import_playlist(playlist_id: str, output_path: str) -> int:
    """Import a public Spotify playlist into a local CSV."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    missing = [
        name
        for name, value in (
            ("SPOTIFY_CLIENT_ID", client_id),
            ("SPOTIFY_CLIENT_SECRET", client_secret),
        )
        if not value
    ]
    if missing:
        raise CatalogImportError(f"Missing required environment variable(s): {', '.join(missing)}")

    token = get_access_token(str(client_id), str(client_secret))
    items = fetch_playlist_tracks(playlist_id, token)
    artist_genres = fetch_artist_genres(_artist_ids(items), token)
    return write_catalog_csv(items, output_path, artist_genres)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Import a public Spotify playlist into a local song CSV.")
    parser.add_argument("--spotify-playlist-id", required=True, help="Public Spotify playlist ID to import.")
    parser.add_argument("--output", required=True, help="CSV path to write, for example data/generated/songs.spotify.csv.")
    args = parser.parse_args(argv)

    try:
        row_count = import_playlist(args.spotify_playlist_id, args.output)
    except CatalogImportError as error:
        parser.exit(1, f"catalog_import: {error}\n")

    print(f"Wrote {row_count} songs to {args.output}")
    return 0


def _catalog_rows(playlist_items: Iterable[Dict], artist_genres: Dict[str, List[str]]) -> List[Dict]:
    rows: List[Dict] = []
    seen_spotify_ids = set()

    for item in playlist_items:
        track = item.get("track") if isinstance(item, dict) else None
        if not _is_importable_track(track):
            continue

        spotify_id = track["id"]
        if spotify_id in seen_spotify_ids:
            continue
        seen_spotify_ids.add(spotify_id)

        rows.append(_track_to_row(track, len(rows) + 1, artist_genres))

    return rows


def _artist_ids(playlist_items: Iterable[Dict]) -> List[str]:
    ids: List[str] = []
    for item in playlist_items:
        track = item.get("track") if isinstance(item, dict) else None
        if not _is_importable_track(track):
            continue
        for artist in track.get("artists", []):
            if isinstance(artist, dict) and artist.get("id"):
                ids.append(str(artist["id"]))
    return ids


def _is_importable_track(track: Optional[Dict]) -> bool:
    if not isinstance(track, dict):
        return False
    if track.get("type") != "track":
        return False
    if track.get("is_local"):
        return False
    if not track.get("id"):
        return False
    if track.get("is_playable") is False:
        return False
    if "available_markets" in track and track.get("available_markets") == []:
        return False
    return True


def _track_to_row(track: Dict, row_id: int, artist_genres: Dict[str, List[str]]) -> Dict:
    album = track.get("album") or {}
    artists = track.get("artists") or []
    first_artist = artists[0].get("name", "") if artists and isinstance(artists[0], dict) else ""
    first_artist_id = artists[0].get("id", "") if artists and isinstance(artists[0], dict) else ""
    spotify_genres = artist_genres.get(first_artist_id, [])
    external_urls = track.get("external_urls") or {}
    external_ids = track.get("external_ids") or {}

    return {
        "id": row_id,
        "title": track.get("name", ""),
        "artist": first_artist,
        "album": album.get("name", ""),
        "genre": _broad_genre(spotify_genres),
        "artist_genres": "; ".join(spotify_genres),
        "mood": "unknown",
        "energy": 0.5,
        "tempo_bpm": 120,
        "valence": 0.5,
        "danceability": 0.5,
        "acousticness": 0.5,
        "duration_sec": int((track.get("duration_ms") or 0) / 1000),
        "release_year": _release_year(album.get("release_date")),
        "popularity": _normalized_popularity(track.get("popularity")),
        "explicit": str(bool(track.get("explicit"))).lower(),
        "spotify_id": track.get("id", ""),
        "spotify_url": external_urls.get("spotify", ""),
        "isrc": external_ids.get("isrc", ""),
        "metadata_source": "spotify",
    }


def _broad_genre(spotify_genres: List[str]) -> str:
    """Map Spotify's artist genre labels to a smaller recommender-friendly genre."""
    joined = " ".join(spotify_genres).lower()
    for broad_genre, keywords in GENRE_KEYWORD_MAP:
        if any(keyword in joined for keyword in keywords):
            return broad_genre
    if spotify_genres:
        return spotify_genres[0]
    return "unknown"


def _release_year(release_date: object) -> int:
    if not release_date:
        return 0
    try:
        return int(str(release_date)[:4])
    except ValueError:
        return 0


def _normalized_popularity(popularity: object) -> float:
    try:
        value = float(popularity)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value / 100.0))


def _raise_for_status(response, message: str) -> None:
    status_code = getattr(response, "status_code", 200)
    if status_code >= 400:
        raise CatalogImportError(f"{message}: HTTP {status_code}")
    try:
        response.raise_for_status()
    except requests.RequestException as error:
        raise CatalogImportError(f"{message}: {error}") from error


def _get_with_retries(url: str, headers: Dict[str, str], params: Optional[Dict[str, object]]):
    for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
        response = requests.get(url, headers=headers, params=params, timeout=20)
        if getattr(response, "status_code", 200) != 429 or attempt == MAX_REQUEST_ATTEMPTS:
            return response
        retry_after = response.headers.get("Retry-After", "1")
        try:
            delay = max(float(retry_after), 0.0)
        except ValueError:
            delay = 1.0
        time.sleep(delay)
    return response


if __name__ == "__main__":
    sys.exit(main())
