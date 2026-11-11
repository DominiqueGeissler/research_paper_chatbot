import sys
from pathlib import Path
from itertools import chain

import chromadb
import ollama
import streamlit as st

# Let this file import code from src/ (explained below)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.generation.ask import (  # noqa: E402
    CHAT_MODEL,
    COLLECTION_NAME,
    DB_PATH,
    SYSTEM_PROMPT,
    build_prompt,
    correct_spelling,
    retrieve,
)

st.set_page_config(page_title="Research Paper Assistant")
st.title("Ask about my research")
st.caption("Answers come only from my papers, with the sources they used.")


@st.cache_resource
def get_collection():
    # Cached so the database is opened once, not on every question
    client = chromadb.PersistentClient(path=str(DB_PATH))
    return client.get_collection(COLLECTION_NAME)


def stream_answer(messages):
    for part in ollama.chat(
        model=CHAT_MODEL,
        messages=messages,
        stream=True,
        options={"temperature": 0.1, "num_ctx": 4096},
    ):
        yield part["message"]["content"]


def show_sources(sources):
    with st.expander("Sources"):
        for i, s in enumerate(sources, start=1):
            st.markdown(f"**[{i}] {s['paper']}, page {s['page']}**")
            st.caption(s["text"][:300] + "...")


# Chat history, kept between reruns
if "history" not in st.session_state:
    st.session_state.history = []

# Redraw the conversation so far
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("searched_for"):
            st.caption(f"Searched for: {msg['searched_for']}")
        if msg.get("sources"):
            show_sources(msg["sources"])

# Handle a new question
if question := st.chat_input("Ask a question about the papers"):
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.history.append({"role": "user", "content": question})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            corrected = correct_spelling(question)
            sources = retrieve(get_collection(), corrected)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(question, sources)},
            ]
            stream = stream_answer(messages)
            first_chunk = next(stream, "")

        answer = st.write_stream(chain([first_chunk], stream))
        searched_for = corrected if corrected != question else None
        if searched_for:
            st.caption(f"Searched for: {searched_for}")
        show_sources(sources)

    st.session_state.history.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "searched_for": searched_for,
        }
    )

    st.session_state.history.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )