import json
from pathlib import Path

from pypdf import PdfReader

# Paths are relative to the project root, so the script works
# no matter which folder you run it from.
ROOT = Path(__file__).resolve().parents[2]
PAPERS_DIR = ROOT / "data" / "papers"
OUTPUT_FILE = ROOT / "data" / "chunks.json"

CHUNK_SIZE = 1000     # characters per chunk
CHUNK_OVERLAP = 200   # characters shared between neighbouring chunks


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Cut text into overlapping pieces so sentences at the
    edges of a chunk aren't lost."""
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def main():
    all_chunks = []

    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {PAPERS_DIR}")
        return

    for pdf_path in pdf_files:
        reader = PdfReader(pdf_path)
        count_before = len(all_chunks)

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = " ".join(text.split())  # collapse messy whitespace
            if not text:
                continue

            for i, chunk in enumerate(split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)):
                all_chunks.append({
                    "id": f"{pdf_path.stem}_p{page_num}_c{i}",
                    "paper": pdf_path.name,
                    "page": page_num,
                    "text": chunk,
                })

        print(f"{pdf_path.name}: {len(reader.pages)} pages, "
              f"{len(all_chunks) - count_before} chunks")

    OUTPUT_FILE.write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nSaved {len(all_chunks)} chunks to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()