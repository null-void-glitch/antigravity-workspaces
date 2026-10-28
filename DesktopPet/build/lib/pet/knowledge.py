"""
knowledge.py — Obsidian vault RAG + persistent memories.

Indexing runs synchronously with a progress callback (no QThread). Embeddings
use ChromaDB's bundled local sentence-transformers model — no API keys needed
for retrieval, so everything stays offline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Callable

import chromadb
from chromadb.config import Settings as ChromaSettings

from pet.config import CONFIG_DIR

log = logging.getLogger(__name__)

DB_DIR = CONFIG_DIR / "chroma_db"
MEMORIES_FILE = CONFIG_DIR / "memories.json"
COLLECTION_NAME = "obsidian_local"

CHUNK_SIZE = 500          # target tokens per chunk
CHUNK_OVERLAP = 50        # overlap in tokens
CHAR_PER_TOKEN = 4        # rough chars-per-token estimate
TOP_K = 5                 # number of chunks to retrieve

# Distance ceiling for ChromaDB cosine results (local sentence-transformers spread).
SIMILARITY_THRESHOLD = 1.2

DEFAULT_EXCLUDES = {".obsidian", ".trash", ".git", "node_modules"}

# on_progress(current, total) is called for each file as it's processed.
ProgressFn = Callable[[int, int], None]


class KnowledgeBase:
    """Vault indexing, retrieval, and persistent memory storage."""

    def __init__(self) -> None:
        self._chroma_client: chromadb.PersistentClient | None = None
        self._collection = None
        self._memories: list[str] = self._load_memories()

    # ── Memories ──────────────────────────────────────────────────────────

    @staticmethod
    def _load_memories() -> list[str]:
        if MEMORIES_FILE.exists():
            try:
                data = json.loads(MEMORIES_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [str(m) for m in data]
            except Exception as exc:
                log.warning("Failed to load memories: %s", exc)
        return []

    def _save_memories(self) -> None:
        try:
            MEMORIES_FILE.parent.mkdir(parents=True, exist_ok=True)
            MEMORIES_FILE.write_text(
                json.dumps(self._memories, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            log.warning("Failed to save memories: %s", exc)

    def add_memory(self, text: str) -> None:
        """Append a new memory and persist."""
        text = text.strip()
        if text and text not in self._memories:
            self._memories.append(text)
            self._save_memories()
            log.info("Memory saved: %s", text[:80])

    def remove_memory(self, index: int) -> bool:
        """Remove memory at *index*; returns True if it existed."""
        if 0 <= index < len(self._memories):
            del self._memories[index]
            self._save_memories()
            return True
        return False

    def set_memories(self, memories: list[str]) -> None:
        """Replace the full memory list and persist."""
        self._memories = [m.strip() for m in memories if m.strip()]
        self._save_memories()

    def reload_memories(self) -> None:
        """Reload memories from disk (e.g. after external edit)."""
        self._memories = self._load_memories()

    def get_memories(self) -> list[str]:
        """Return all stored memory strings."""
        return list(self._memories)

    # ── Indexing ──────────────────────────────────────────────────────────

    def index_vault(
        self,
        vault_path: str,
        on_progress: ProgressFn | None = None,
    ) -> int:
        """Synchronously index a vault directory. Returns count of files indexed.

        on_progress(current, total) is called for each file processed.
        Skips files whose hash hasn't changed since the last index.
        """
        vault = Path(vault_path).expanduser()
        if not vault.is_dir():
            raise ValueError(f"Vault path is not a directory: {vault}")

        client = chromadb.PersistentClient(
            path=str(DB_DIR),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        md_files = sorted(
            p for p in vault.rglob("*.md")
            if not any(ex in p.parts for ex in DEFAULT_EXCLUDES)
        )
        total = len(md_files)
        if total == 0:
            return 0

        existing_ids: set[str] = set()
        try:
            existing = collection.get()
            if existing and existing["ids"]:
                existing_ids = set(existing["ids"])
        except Exception:
            pass

        indexed = 0

        for i, md_path in enumerate(md_files):
            if on_progress is not None:
                try:
                    on_progress(i + 1, total)
                except Exception as exc:
                    log.warning("on_progress callback failed: %s", exc)

            text = md_path.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                continue

            chunks = _chunk_text(text)
            if not chunks:
                continue

            fhash = _file_hash(md_path)
            rel = str(md_path.relative_to(vault))
            chunk_ids = [f"{rel}::{ci}::{fhash}" for ci in range(len(chunks))]

            # Skip if nothing changed.
            if all(cid in existing_ids for cid in chunk_ids):
                continue

            # Remove stale chunks (different hash) for this file.
            stale = [eid for eid in existing_ids if eid.startswith(f"{rel}::")]
            if stale:
                collection.delete(ids=list(stale))

            collection.upsert(
                ids=chunk_ids,
                documents=chunks,
                metadatas=[{"source": rel, "chunk": ci}
                           for ci in range(len(chunks))],
            )
            indexed += 1

        # Drop cached client/collection so next retrieval reads the fresh DB.
        self._chroma_client = None
        self._collection = None
        return indexed

    # ── Retrieval ─────────────────────────────────────────────────────────

    def get_relevant_context(self, query: str, n_results: int = TOP_K) -> str:
        """Return a formatted vault context string for *query*, or '' if nothing found."""
        if not DB_DIR.exists():
            return ""

        if self._collection is None:
            try:
                self._chroma_client = chromadb.PersistentClient(
                    path=str(DB_DIR),
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
                self._collection = self._chroma_client.get_collection(
                    name=COLLECTION_NAME,
                )
            except Exception as exc:
                log.warning("Failed to open ChromaDB collection: %s", exc)
                return ""

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
            )
        except Exception as exc:
            log.warning("ChromaDB query failed: %s", exc)
            return ""

        if not results or not results["documents"] or not results["documents"][0]:
            return ""

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [None] * len(docs)

        parts: list[str] = []
        for doc, meta, dist in zip(docs, metas, distances):
            if dist is not None and dist > SIMILARITY_THRESHOLD:
                continue
            source = meta.get("source", "unknown")
            parts.append(f"[Source: {source}]\n{doc}")

        return "\n\n---\n\n".join(parts)

    # ── Cleanup / status ─────────────────────────────────────────────────

    def clear_index(self) -> None:
        """Delete the entire ChromaDB database."""
        if DB_DIR.exists():
            shutil.rmtree(DB_DIR, ignore_errors=True)
        self._chroma_client = None
        self._collection = None

    def collection_count(self) -> int:
        """Return number of indexed chunks (0 if no collection exists)."""
        if not DB_DIR.exists():
            return 0
        try:
            client = chromadb.PersistentClient(
                path=str(DB_DIR),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            collection = client.get_collection(name=COLLECTION_NAME)
            return collection.count()
        except Exception:
            return 0


# ── Internal helpers ─────────────────────────────────────────────────────

def _chunk_text(
    text: str,
    chunk_chars: int = CHUNK_SIZE * CHAR_PER_TOKEN,
    overlap_chars: int = CHUNK_OVERLAP * CHAR_PER_TOKEN,
) -> list[str]:
    """Split *text* into overlapping chunks on paragraph boundaries."""
    if not text.strip():
        return []

    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= chunk_chars:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > chunk_chars:
                for i in range(0, len(para), chunk_chars - overlap_chars):
                    chunks.append(para[i:i + chunk_chars])
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


def _file_hash(path: Path) -> str:
    """Short hash of file path + mtime + size for change detection."""
    stat = path.stat()
    key = f"{path}:{stat.st_mtime_ns}:{stat.st_size}"
    return hashlib.md5(key.encode()).hexdigest()
