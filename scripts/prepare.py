import time

import ollama

from src.generation.ask import CHAT_MODEL, DB_PATH, EMBED_MODEL
from src.ingest.ingest import main as run_ingest
from src.retrieval.build_index import main as run_build_index


def wait_for_ollama():
    for _ in range(30):
        try:
            ollama.list()
            return
        except Exception:
            print("Waiting for Ollama to start...", flush=True)
            time.sleep(2)
    raise RuntimeError("Could not reach Ollama.")


def main():
    wait_for_ollama()

    for model in (EMBED_MODEL, CHAT_MODEL):
        print(f"Checking model {model} (first run downloads it, may take a while)...",
              flush=True)
        ollama.pull(model)

    if DB_PATH.exists() and any(DB_PATH.iterdir()):
        print("Search index found, skipping build.", flush=True)
    else:
        print("Building search index from the papers...", flush=True)
        run_ingest()
        run_build_index()

    print("Setup done. Open http://localhost:8501", flush=True)


if __name__ == "__main__":
    main()