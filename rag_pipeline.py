"""Policy ingestion and lightweight persistent RAG index.

The production path uses SentenceTransformers embeddings and cosine similarity.
A deterministic lexical fallback is included so the application remains usable
for local smoke tests when the embedding package/model is unavailable.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from config import (
    EMBEDDING_MODEL,
    INDEX_DIR,
    POLICY_DIR,
    RETRIEVAL_K,
    USE_EMBEDDINGS,
)
from document_loader import load_sections


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    title: str
    section: str
    text: str
    source_file: str


class PolicyRAG:
    """Small RAG implementation designed for free-tier deployment."""

    def __init__(self, policy_dir: Path = POLICY_DIR, index_dir: Path = INDEX_DIR):
        self.policy_dir = Path(policy_dir)
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.chunks: list[Chunk] = []
        self.embeddings: np.ndarray | None = None
        self.embedder = None
        self.vector_store = None
        self._load_or_build()
        self._load_embedder()

    def _load_or_build(self) -> None:
        metadata_path = self.index_dir / "chunks.json"
        vectors_path = self.index_dir / "embeddings.npy"

        # In lightweight deployment mode, always rebuild the
        # small lexical index so it matches the current vocabulary.
        if not USE_EMBEDDINGS:
            self.build()
            return

    def _load_or_build(self) -> None:
        metadata_path = self.index_dir / "chunks.json"
        vectors_path = self.index_dir / "embeddings.npy"

        # In lightweight deployment mode, always rebuild the
        # small lexical index so it matches the current vocabulary.
        if not USE_EMBEDDINGS:
            self.build()
            return

        if metadata_path.exists() and vectors_path.exists():
            self.chunks = [
                Chunk(**item)
                for item in json.loads(
                    metadata_path.read_text(encoding="utf-8")
                )
            ]
            self.embeddings = np.load(vectors_path)

            try:
                import chromadb

                client = chromadb.PersistentClient(
                    path=str(self.index_dir / "chroma")
                )
                self.vector_store = client.get_or_create_collection(
                    "hr_policy"
                )
            except Exception:
                self.vector_store = None

            return

        self.build()

    def _load_embedder(self):
        if not USE_EMBEDDINGS:
            self.embedder = False
            return self.embedder

        if self.embedder is None:
            try:
                from sentence_transformers import SentenceTransformer

                self.embedder = SentenceTransformer(EMBEDDING_MODEL)
            except Exception:
                self.embedder = False
        return self.embedder

    @staticmethod
    def _chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
        """Split text into deterministic overlapping word windows."""
        words = text.split()
        if len(words) <= size:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(words):
            end = min(len(words), start + size)
            chunks.append(" ".join(words[start:end]))
            if end == len(words):
                break
            start = max(0, end - overlap)
        return chunks

    def _lexical_vectors(self, texts: list[str], vocab: list[str] | None = None) -> np.ndarray:
        """Deterministic vectors used only when embeddings are unavailable."""
        token_sets = [re.findall(r"[a-z0-9]+", t.lower()) for t in texts]
        if vocab is None:
            vocab = sorted({token for tokens in token_sets for token in tokens})
        index = {word: i for i, word in enumerate(vocab)}
        matrix = np.zeros((len(texts), len(vocab)), dtype=np.float32)
        for row, tokens in enumerate(token_sets):
            for token in tokens:
                matrix[row, index[token]] += 1.0
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.maximum(norms, 1e-8)

    def _embed(self, texts: list[str]) -> np.ndarray:
        model = self._load_embedder()
        if model:
            return np.asarray(model.encode(texts, normalize_embeddings=True), dtype=np.float32)
        if self.chunks:
            corpus_text = [chunk.text for chunk in self.chunks]
            vocab = sorted({token for text in corpus_text for token in re.findall(r"[a-z0-9]+", text.lower())})
            return self._lexical_vectors(texts, vocab)
        return self._lexical_vectors(texts)

    def build(self) -> dict[str, Any]:
        """Ingest Markdown policy documents, chunk them, embed them and persist the index."""
        chunks: list[Chunk] = []
        for path in sorted(self.policy_dir.glob("*.md")):
            document_id = path.stem
            for section_number, (section, body) in enumerate(load_sections(path), start=1):
                for number, text in enumerate(self._chunk_text(body), start=1):
                    chunks.append(
                        Chunk(
                            chunk_id=f"{document_id}-{section_number}-{number}",
                            document_id=document_id,
                            title=path.stem.replace("_", " ").title(),
                            section=section,
                            text=text,
                            source_file=path.name,
                        )
                    )
        texts = [chunk.text for chunk in chunks]
        self.chunks = chunks
        vectors = self._embed(texts)
        self.embeddings = vectors
        (self.index_dir / "chunks.json").write_text(
            json.dumps([asdict(chunk) for chunk in chunks], indent=2), encoding="utf-8"
        )
        np.save(self.index_dir / "embeddings.npy", vectors)
        # Persist the same vectors in Chroma when the package is available.
        # The NumPy files remain the lightweight fallback for local tests.
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(self.index_dir / "chroma"))
            collection = client.get_or_create_collection("hr_policy")
            collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                embeddings=vectors.tolist(),
                documents=texts,
                metadatas=[
                    {
                        "document_id": chunk.document_id,
                        "title": chunk.title,
                        "section": chunk.section,
                        "source_file": chunk.source_file,
                    }
                    for chunk in chunks
                ],
            )
            self.vector_store = collection
        except Exception:
            self.vector_store = None
        return {"documents": len(set(c.document_id for c in chunks)), "chunks": len(chunks)}

    def search(self, query: str, k: int = RETRIEVAL_K) -> list[dict[str, Any]]:
        """Return top-k policy chunks with citation metadata and similarity."""
        if not query.strip() or not self.chunks or self.embeddings is None:
            return []
        query_vector = self._embed([query])[0]
        if USE_EMBEDDINGS and self.vector_store is not None:
            try:
                response = self.vector_store.query(query_embeddings=[query_vector.tolist()], n_results=k)
                ids = response.get("ids", [[]])[0]
                distances = response.get("distances", [[]])[0]
                lookup = {chunk.chunk_id: chunk for chunk in self.chunks}
                return [
                    {
                        "chunk_id": chunk_id,
                        "document_id": lookup[chunk_id].document_id,
                        "title": lookup[chunk_id].title,
                        "section": lookup[chunk_id].section,
                        "snippet": lookup[chunk_id].text[:700],
                        "score": round(float(1 - distances[i]), 4) if i < len(distances) else None,
                        "source_file": lookup[chunk_id].source_file,
                    }
                    for i, chunk_id in enumerate(ids)
                    if chunk_id in lookup
                ]
            except Exception:
                pass

        scores = self.embeddings @ query_vector
        top_indices = np.argsort(scores)[::-1][:k]
        return [
            {
                "chunk_id": self.chunks[int(idx)].chunk_id,
                "document_id": self.chunks[int(idx)].document_id,
                "title": self.chunks[int(idx)].title,
                "section": self.chunks[int(idx)].section,
                "snippet": self.chunks[int(idx)].text[:700],
                "score": round(float(scores[idx]), 4),
                "source_file": self.chunks[int(idx)].source_file,
            }
            for idx in top_indices
        ]

    def get_section(self, document_id: str, section: str) -> list[dict[str, Any]]:
        """Retrieve a named section from one policy document."""
        section_lower = section.lower()
        matches = [
            c
            for c in self.chunks
            if c.document_id.lower() == document_id.lower() and section_lower in c.section.lower()
        ]
        return [
            {
                "chunk_id": c.chunk_id,
                "document_id": c.document_id,
                "title": c.title,
                "section": c.section,
                "snippet": c.text[:1000],
                "source_file": c.source_file,
            }
            for c in matches
        ]


# A shared instance keeps the web process fast after the first index load.
_rag: PolicyRAG | None = None


def get_rag() -> PolicyRAG:
    global _rag
    if _rag is None:
        _rag = PolicyRAG()
    return _rag


def load_policy_documents() -> list[Chunk]:
    """Compatibility helper used by tests and the existing project workflow."""
    return get_rag().chunks
