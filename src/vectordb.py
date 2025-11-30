# src/vectordb.py
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional

from .embedder_ollama import embed_texts


def get_client(persist_dir: str):
    """
    Create a persistent Chroma client.

    We do NOT configure an embedding_function here, because we handle
    embeddings ourselves via Ollama (see upsert_chunks / query).
    """
    try:
        # Newer Chroma
        return chromadb.PersistentClient(path=persist_dir)
    except AttributeError:
        # Backwards-compatible fallback
        return chromadb.Client(
            Settings(
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            )
        )


def get_collection(client, name: str = "reports"):
    """
    Create or get a collection using cosine similarity.

    Embeddings are supplied manually when adding/querying, so this
    collection is just raw storage + ANN index.
    """
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(collection, chunks: List[Dict]) -> None:
    """
    Upsert chunk documents into Chroma using **Ollama embeddings**.

    - Uses embed_texts(...) from embedder_ollama.py
    - Skips empty chunks
    - Stores all non-text metadata in metadatas
    """
    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict] = []

    for i, ch in enumerate(chunks):
        text = ch.get("text", "")
        if not text or not text.strip():
            # skip empty chunks
            print(f"[WARN] Skipping empty chunk for file {ch.get('file_name')} page {ch.get('page')}")
            continue

        ids.append(f"{ch.get('file_name')}::{ch.get('page')}::{i}")
        docs.append(text)
        metas.append({k: v for k, v in ch.items() if k != "text"})

    if not docs:
        print("[WARN] No non-empty chunks to upsert.")
        return

    # --- Ollama embeddings ---
    print(f"[INFO] Embedding {len(docs)} chunks via Ollama...")
    embeddings = embed_texts(docs)

    if len(embeddings) != len(docs):
        raise RuntimeError(
            f"Embedding count mismatch: {len(embeddings)} embeddings for {len(docs)} docs"
        )

    collection.add(
        ids=ids,
        documents=docs,
        embeddings=embeddings,
        metadatas=metas,
    )
    print(f"[INFO] Upserted {len(docs)} chunks into Chroma.")


def query(
    collection,
    q: str,
    n: int = 8,
    where: Optional[dict] = None,
):
    """
    Query the vector DB using **Ollama embeddings** for the query string.

    We:
      1) Embed the query text via embed_texts([q])
      2) Call collection.query with query_embeddings instead of query_texts
    """
    if not q.strip():
        raise ValueError("Query text is empty.")

    # --- Ollama embeddings for query ---
    q_emb = embed_texts([q])[0]

    return collection.query(
        query_embeddings=[q_emb],
        n_results=n,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
