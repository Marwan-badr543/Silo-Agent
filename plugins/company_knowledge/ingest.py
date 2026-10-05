import asyncio
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from plugins.company_knowledge.embeddings import embed
from plugins.company_knowledge.store import CHROMA_PATH, get_client, new_collection

DOCS_DIR = Path(__file__).parent / "docs"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
# Recursive chunking: cut on a blank line first. A piece still bigger than CHUNK_SIZE is cut on a full stop,
# and one still too big after that is cut on a comma. The separator stays at the end of its chunk.
# The last separator, "", is the hard split: text with no separator at all is cut every CHUNK_SIZE characters.
SEPARATORS = ["\n\n", ".", ",", ""]


def read_chunks(docs_dir: Path) -> list[dict]:
    """Cuts every PDF into chunks. Each chunk keeps its file and page, so answers can name their source."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=SEPARATORS, keep_separator="end"
    )
    chunks = []
    for pdf_path in sorted(docs_dir.glob("*.pdf")):
        for page_number, page in enumerate(PdfReader(pdf_path).pages, start=1):
            # PDFs break lines inside a sentence. Turn those single line breaks into spaces, and keep blank lines.
            text = re.sub(r"(?<!\n)\n(?!\n)", " ", page.extract_text() or "")
            for chunk_text in splitter.split_text(text):
                chunks.append({"source": pdf_path.name, "page": page_number, "text": chunk_text})
    return chunks


async def build_index(docs_dir: Path = DOCS_DIR, chroma_path: Path = CHROMA_PATH) -> int:
    chunks = read_chunks(docs_dir)
    if not chunks:
        raise SystemExit(f"No text found in PDF files in {docs_dir}. Scanned PDFs (images) are not supported.")
    vectors = await embed([chunk["text"] for chunk in chunks], input_type="passage")
    new_collection(get_client(chroma_path)).add(
        ids=[f"{chunk['source']}-p{chunk['page']}-{number}" for number, chunk in enumerate(chunks)],
        embeddings=vectors,
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[{"source": chunk["source"], "page": chunk["page"]} for chunk in chunks],
    )
    return len(chunks)


if __name__ == "__main__":
    print(f"Indexed {asyncio.run(build_index())} chunks into {CHROMA_PATH}")
