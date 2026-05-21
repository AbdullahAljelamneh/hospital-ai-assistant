"""Retrieve relevant chunks from the vector store for a given query."""

import sys
from pathlib import Path
from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import (
    EMBEDDING_MODEL,
    CHROMA_COLLECTION,
    CHROMA_PERSIST_DIR,
    TOP_K_RETRIEVAL,
)


@dataclass
class RetrievalResult:
    text: str
    source: str
    section: str
    distance: float


class HospitalRetriever:
    """Semantic search over the hospital knowledge base."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        self.collection = self.client.get_collection(
            name=CHROMA_COLLECTION, embedding_function=self.embedding_fn
        )

    def retrieve(
        self, query: str, top_k: int = TOP_K_RETRIEVAL
    ) -> list[RetrievalResult]:
        """Find the most relevant chunks for a query."""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        retrieved = []
        for i in range(len(results["ids"][0])):
            retrieved.append(
                RetrievalResult(
                    text=results["documents"][0][i],
                    source=results["metadatas"][0][i]["source"],
                    section=results["metadatas"][0][i]["section"],
                    distance=results["distances"][0][i],
                )
            )

        return retrieved

    def format_context(self, results: list[RetrievalResult]) -> str:
        """Format retrieved chunks into a context string for the LLM."""
        if not results:
            return "No relevant information found in the knowledge base."

        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[Source {i}: {r.source} — {r.section}]\n{r.text}")

        return "\n\n---\n\n".join(context_parts)
