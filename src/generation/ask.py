from pathlib import Path

import chromadb
import ollama
import difflib

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "chroma_db"

COLLECTION_NAME = "papers"
EMBED_MODEL = "nomic-embed-text"
CHAT_MODEL = "llama3.2:3b"
TOP_K = 5  # how many chunks to give the model

SYSTEM_PROMPT = """You answer questions about a set of research papers.
Use ONLY the numbered sources provided in the user's message.
After each claim, cite its source number in square brackets, like [1] or [2][3].
If the sources do not contain the answer, reply exactly:
"I couldn't find that in the papers."
Do not use outside knowledge. Keep answers concise."""

SPELLING_PROMPT = """You fix spelling mistakes. Rules:
- Only correct misspelled words. Do not rephrase, reorder, add, or remove words.
- Keep names, acronyms, and technical terms as they are unless clearly misspelled.
- If there are no mistakes, return the text exactly as given.
- Output ONLY the corrected text, with no explanation and no quotes.

Example input: how dose propoganda spred on socail media
Example output: how does propaganda spread on social media"""

# How similar the corrected text must be to the original (0 to 1).
# Lower values allow bigger changes. Spelling fixes usually stay above 0.85.
MIN_SIMILARITY = 0.8


def correct_spelling(question: str) -> str:
    response = ollama.chat(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SPELLING_PROMPT},
            {"role": "user", "content": question},
        ],
        options={"temperature": 0},  # no creativity wanted here
    )
    corrected = response["message"]["content"].strip().strip('"')

    # Safety check: reject anything that changed too much
    similarity = difflib.SequenceMatcher(
        None, question.lower(), corrected.lower()
    ).ratio()
    if not corrected or similarity < MIN_SIMILARITY:
        return question
    return corrected

def retrieve(collection, question: str) -> list[dict]:
    query_embedding = ollama.embed(
        model=EMBED_MODEL, input=[f"search_query: {question}"]
    )["embeddings"]
    results = collection.query(query_embeddings=query_embedding, n_results=TOP_K)

    return [
        {"text": doc, "paper": meta["paper"], "page": meta["page"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def build_prompt(question: str, sources: list[dict]) -> str:
    context = "\n\n".join(
        f"[{i}] ({s['paper']}, page {s['page']})\n{s['text']}"
        for i, s in enumerate(sources, start=1)
    )
    return f"Sources:\n{context}\n\nQuestion: {question}"


def main():
    client = chromadb.PersistentClient(path=str(DB_PATH))
    collection = client.get_collection(COLLECTION_NAME)

    while True:
        question = input("\nAsk a question (or press Enter to quit): ").strip()
        if not question:
            break

        corrected = correct_spelling(question)
        if corrected != question:
            print(f"(Searching for: {corrected})")
        sources = retrieve(collection, corrected)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, sources)},
        ]

        print("\nAnswer: ", end="", flush=True)
        # stream=True prints the answer word by word as it's generated
        for part in ollama.chat(
            model=CHAT_MODEL,
            messages=messages,
            stream=True,
            options={
                "temperature": 0.1,  # low = more factual, less creative
                "num_ctx": 4096,     # room for the prompt + sources
            },
        ):
            print(part["message"]["content"], end="", flush=True)

        print("\n\nSources:")
        for i, s in enumerate(sources, start=1):
            print(f"  [{i}] {s['paper']}, page {s['page']}")


if __name__ == "__main__":
    main()