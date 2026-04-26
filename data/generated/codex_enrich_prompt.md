# Codex Catalog Enrichment Prompt

Use this prompt with `data/generated/songs.spotify.csv` after importing a public Spotify playlist.

Review or fill these columns for every row:

- `genre`
- `mood`
- `energy`
- `tempo_bpm`
- `valence`
- `danceability`
- `acousticness`

Allowed `genre` values:

- `afrobeat`
- `ambient`
- `blues`
- `chamber pop`
- `classical`
- `folk`
- `hip hop`
- `house`
- `indie pop`
- `jazz`
- `lofi`
- `metal`
- `pop`
- `r&b`
- `reggaeton`
- `rock`
- `synthwave`
- `unknown`

Allowed `mood` values:

- `chill`
- `euphoric`
- `focused`
- `happy`
- `intense`
- `joyful`
- `moody`
- `playful`
- `rebellious`
- `relaxed`
- `romantic`
- `serene`
- `soulful`
- `wistful`
- `unknown`

Rules:

- Keep Spotify-populated columns unchanged.
- Keep `artist_genres` unchanged; it is raw Spotify artist metadata.
- `genre` may already be mapped from `artist_genres`; correct it only when the mapping is clearly wrong.
- Use only the allowed `genre` and `mood` values above.
- Use `unknown` only when there is not enough information to make a reasonable call.
- Use `energy`, `valence`, `danceability`, and `acousticness` values from `0.0` to `1.0`.
- Use realistic `tempo_bpm` values, usually from `40` to `220`.
- Prefer conservative estimates over false precision. It is acceptable for inferred numeric values to be approximate.
- Set `metadata_source` to `spotify+codex` for enriched rows.
- Preserve the CSV header and row order.
- Preserve `id`, `title`, `artist`, `album`, `artist_genres`, `duration_sec`, `release_year`, `popularity`, `explicit`, `spotify_id`, `spotify_url`, and `isrc` exactly.
- If working in chunks, preserve the same header and row order for the rows in that chunk.
- For rows that cannot be confidently enriched, keep uncertain fields as `unknown` or neutral numeric defaults instead of guessing aggressively.
- Return valid CSV only. Quote fields when needed, especially values containing commas, quotes, or line breaks.
- Do not add markdown fences, explanations, notes, or extra columns in the output.
