# Model Card: AI Playlist Copilot

## 1. Model Name

AI Playlist Copilot, built on the original Music Recommender Simulation.

## 2. Intended Use

The system recommends songs from a small local CSV catalog based on a user's listening request. It is intended for classroom exploration of recommender systems, RAG, structured profile generation, validation, and reliability communication.

It is not intended for production music recommendation or real personalization. It does not learn from listening history, behavior, skips, likes, or collaborative signals.

## 3. System Overview

The system has two layers:

- Transparent recommender: `recommend_songs` ranks songs with weighted content-based scoring.
- Copilot layer: natural-language requests are retrieved against local context docs, converted into a validated profile, planned into a playlist mode, audited, and displayed in Streamlit.

The scoring engine uses exact matches for genre and mood, plus numeric closeness for energy, acousticness, tempo, duration, release year, and popularity. The Copilot does not replace this scorer. It only creates the profile that the scorer consumes.

## 4. Data

The catalog is `data/songs.csv`. It contains 18 songs with fields for title, artist, genre, mood, energy, tempo, valence, danceability, acousticness, duration, release year, popularity, and an `explicit` boolean.

The app can also run against a generated local CSV through `SONG_PATH`. Spotify-imported catalogs contain real catalog metadata, while recommender-specific fields such as genre, mood, energy, tempo, valence, danceability, and acousticness may be manually or Codex-assisted enriched. Those values are metadata inputs, not learned features, and the recommender does not distinguish hand-authored values from LLM-assisted edits.

The retrieval layer uses 8 local YAML context docs:

- `study`
- `focus`
- `workout`
- `party`
- `sleep`
- `sad`
- `commute`
- `relax`

Each context doc includes weighted keywords, a short summary, numeric target ranges, and mood hints.

## 5. Profile Generation

If `GEMINI_API_KEY` is set, the system attempts to use Gemini to produce a structured profile. Gemini output is validated against the current CSV catalog and numeric bounds. Unsupported genres, unsupported moods, invalid numerics, network errors, or timeouts trigger fallback.

If Gemini is unavailable or invalid, the deterministic fallback parser:

- tokenizes the request
- detects known genres, moods, and intents
- blends retrieved context ranges into target values
- clamps numeric values
- warns on vague or contradictory requests

The final profile is scorer-compatible and includes fields such as `genre`, `mood`, `energy`, `tempo_bpm`, and `acousticness`.

## 6. Strengths

The system works best for requests that map clearly onto the small catalog or context docs, such as:

- `upbeat workout music`
- `quiet study music`
- `calm sleep music`
- `happy pop music`

It is also transparent. Every recommendation keeps its score and reason strings, and the audit explains reliability warnings.

## 7. Limitations and Bias

The catalog is very small and hand-built, so it is biased toward included genres, moods, and artists. A user asking for music outside that catalog will receive approximate matches.

The system does not understand lyrics, language, culture, artist background, production style, or personal listening history. It also cannot know whether a song is truly appropriate for a setting beyond the metadata provided.

The Gemini tier may interpret expressive requests better than the fallback parser, but it is still constrained by the local catalog. Validation prevents unsupported output from entering the scorer, but fallback recommendations can still be generic when the request is vague.

## 8. Reliability Audit

The audit confidence is heuristic, not statistical. It averages:

- top recommendation score strength
- exact genre and mood availability in the filtered catalog
- candidate pool size

It then lowers confidence for vague requests, contradictions, heavy explicit filtering, narrow score gaps, and recommendations that mainly match numeric features instead of genre or mood.

This confidence should be read as a debugging and transparency aid, not a probability of user satisfaction.

## 9. Evaluation

The automated tests cover:

- original recommender behavior
- CSV parsing and missing `explicit` backward compatibility
- context retrieval
- fallback profile generation
- mocked Gemini invalid-output fallback
- close match, variety, and arc playlist generation
- audit confidence and warning behavior

Manual evaluation should include:

- running `python3 -m src.main`
- running `streamlit run src/app.py`
- trying direct fallback prompts like `upbeat workout music`
- trying indirect Gemini prompts like `drive home after a long day`
- confirming request logs omit API keys

## 10. Future Work

Useful next steps would include a larger catalog, better genre and mood taxonomy, embeddings for retrieval, richer explicit/content metadata, user feedback loops, and playlist refinement across multiple turns.

For production use, the biggest change would be replacing the tiny CSV with a representative dataset and evaluating recommendations against real user behavior instead of only handcrafted examples.

## 11. AI Collaboration Reflection

AI assistance was useful for turning the assignment into a multi-module system, but the important engineering guardrail was keeping the original recommender as the single source of truth. That made the new AI-facing layers easier to test and easier to explain.
