import json
from pathlib import Path

import chromadb
import ollama

ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = ROOT / "data" / "chunks.json"
DB_PATH = ROOT / "data" / "chroma_db"

COLLECTION_NAME = "papers"
EMBED_MODEL = "nomic-embed-text"
BATCH_SIZE = 32  # embed this many chunks per call to Ollama


def embed_documents(texts: list[str]) -> list[list[float]]:
    # nomic-embed-text works best when you tell it whether the text
    # is a document being stored or a query being searched.
    inputs = [f"search_document: {t}" for t in texts]
    response = ollama.embed(model=EMBED_MODEL, input=inputs)
    return response["embeddings"]


def main():
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    client = chromadb.PersistentClient(path=str(DB_PATH))

    # Start fresh each time so re-running doesn't create duplicates.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        embeddings = embed_documents([c["text"] for c in batch])

        collection.add(
            ids=[c["id"] for c in batch],
            embeddings=embeddings,
            documents=[c["text"] for c in batch],
            metadatas=[{"paper": c["paper"], "page": c["page"]} for c in batch],
        )
        print(f"Embedded {min(start + BATCH_SIZE, len(chunks))}/{len(chunks)}")

    print(f"\nDone. {collection.count()} chunks stored in {DB_PATH}")


if __name__ == "__main__":
    main()