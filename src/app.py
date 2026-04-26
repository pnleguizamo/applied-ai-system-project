import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from src.playlist import generate_playlist
from src.rag import load_context_docs
from src.recommender import load_songs


SONG_PATH = os.environ.get("SONG_PATH", "data/songs.csv")
CONTEXT_PATH = "data/context_docs"
LOG_PATH = Path("logs/playlist_requests.jsonl")


@st.cache_data
def cached_songs():
    return load_songs(SONG_PATH)


@st.cache_data
def cached_contexts():
    return load_context_docs(CONTEXT_PATH)


def _serializable_profile(profile):
    return {key: value for key, value in profile.items() if key != "latency_ms"}


def _log_request(user_request, result, latency_ms):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request": user_request,
        "parser_tier": result.get("parser_tier"),
        "parser_fallback_reason": result.get("parser_fallback_reason"),
        "model_name": result["profile"].get("model_name"),
        "latency_ms": latency_ms,
        "retrieved_context_ids": [context.get("id") for context in result["retrieved_contexts"]],
        "profile": _serializable_profile(result["profile"]),
        "recommendation_ids": [song["id"] for song, _, _ in result["recommendations"]],
        "confidence": result["audit"]["confidence"],
        "warnings": result["audit"]["warnings"],
    }
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record) + "\n")


def _recommendation_rows(result):
    rows = []
    for song, score, reasons in result["recommendations"]:
        rows.append(
            {
                "Title": song["title"],
                "Artist": song["artist"],
                "Genre": song["genre"],
                "Mood": song["mood"],
                "Score": round(score, 2),
                "Reasons": " | ".join(reasons),
            }
        )
    return rows


def main():
    st.set_page_config(page_title="AI Playlist Copilot", page_icon="music", layout="wide")
    st.title("AI Playlist Copilot")

    songs = cached_songs()
    contexts = cached_contexts()

    with st.sidebar:
        length = st.number_input("Playlist length", min_value=1, max_value=25, value=10, step=1)
        allow_explicit = st.checkbox("Allow explicit songs", value=False)
        mode = st.selectbox("Mode", ["close_match", "variety", "arc"])
        force_fallback = st.checkbox("Force fallback parser", value=False)

    user_request = st.text_area("What do you want to listen to?", value="upbeat workout music", height=110)

    if st.button("Generate playlist", type="primary"):
        started = time.perf_counter()
        result = generate_playlist(
            user_request,
            songs,
            contexts,
            length=int(length),
            mode=mode,
            allow_explicit=allow_explicit,
            force_fallback=force_fallback,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)
        _log_request(user_request, result, latency_ms)

        parser_label = "Parsed by Gemini" if result["parser_tier"] == "gemini" else "Parsed by fallback"
        st.caption(parser_label)
        if result.get("parser_fallback_reason"):
            st.caption(result["parser_fallback_reason"])

        left, right = st.columns([2, 1])
        with left:
            st.subheader("Recommendations")
            st.dataframe(_recommendation_rows(result), use_container_width=True, hide_index=True)
        with right:
            st.subheader("Reliability")
            st.metric("Confidence", f"{result['audit']['confidence']:.2f}")
            st.write(result["audit"]["audit_summary"])
            if result["audit"]["warnings"]:
                st.warning("\n".join(result["audit"]["warnings"]))

        st.subheader("Profile")
        if "staged_profiles" in result:
            st.json(result["staged_profiles"])
        else:
            st.json(result["profile"])

        st.subheader("Retrieved Contexts")
        st.write([context.get("id") for context in result["retrieved_contexts"]])


if __name__ == "__main__":
    main()
