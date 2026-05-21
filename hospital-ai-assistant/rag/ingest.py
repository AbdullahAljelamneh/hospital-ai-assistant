"""Ingest hospital documents into ChromaDB vector store.

Usage:
    python rag/ingest.py
"""

import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    EMBEDDING_MODEL,
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from rag.chunker import chunk_markdown


def ingest_documents(docs_dir: str = "data/sample_docs"):
    """Read, chunk, and embed all markdown docs into ChromaDB."""

    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    try:
        client.delete_collection(CHROMA_COLLECTION)
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_fn,
        metadata={"description": "Hospital knowledge base for AI call center"},
    )

    all_chunks = []
    docs_path = Path(docs_dir)

    for md_file in docs_path.glob("*.md"):
        print(f"Processing: {md_file.name}")
        text = md_file.read_text(encoding="utf-8")
        chunks = chunk_markdown(
            text=text, source=md_file.name, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP
        )
        all_chunks.extend(chunks)
        print(f"   {len(chunks)} chunks")

    if not all_chunks:
        print("No documents found in", docs_dir)
        return

    collection.add(
        ids=[c.chunk_id for c in all_chunks],
        documents=[c.text for c in all_chunks],
        metadatas=[{"source": c.source, "section": c.section} for c in all_chunks],
    )

    print(
        f"\nIngested {len(all_chunks)} chunks from {len(list(docs_path.glob('*.md')))} documents"
    )


if __name__ == "__main__":
    ingest_documents()
