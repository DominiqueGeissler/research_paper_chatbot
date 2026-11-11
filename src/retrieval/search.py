from pathlib import Path

import chromadb
import ollama

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "chroma_db"
COLLECTION_NAME = "papers"
EMBED_MODEL = "nomic-embed-text"


def main():
    client = chromadb.PersistentClient(path=str(DB_PATH))
    collection = client.get_collection(COLLECTION_NAME)

    while True:
        question = input("\nAsk a question (or press Enter to quit): ").strip()
        if not question:
            break

        query_embedding = ollama.embed(
            model=EMBED_MODEL, input=[f"search_query: {question}"]
        )["embeddings"]

        results = collection.query(query_embeddings=query_embedding, n_results=5)

        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            print(f"\n--- {meta['paper']} (page {meta['page']}) | distance {dist:.3f}")
            print(doc[:300] + "...")


if __name__ == "__main__":
    main()