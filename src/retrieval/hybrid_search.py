# src/retrieval/hybrid_search.py

"""
Hybrid retrieval: Vector search + BM25 re-ranking.
"""

from typing import List, Dict, Optional

try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False
    print("[WARN] rank-bm25 not installed. BM25 re-ranking disabled.")


def preprocess_for_bm25(text: str) -> List[str]:
    """
    ESG-optimized tokenization for BM25.
    Preserves domain-specific multi-word terms.
    """
    import re

    # Preserve multi-word terms
    text = text.replace("Scope 1", "Scope_1")
    text = text.replace("Scope 2", "Scope_2")
    text = text.replace("Scope 3", "Scope_3")
    text = text.replace("tCO2e", "tCO2e_emission")
    text = text.replace("GHG Protocol", "GHG_Protocol")
    text = text.replace("carbon intensity", "carbon_intensity")
    text = text.replace("emission factor", "emission_factor")

    # Remove special characters but keep numbers
    text = re.sub(r'[^\w\s_]', ' ', text)

    # Tokenize
    tokens = text.lower().split()

    # Remove stopwords (optional)
    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
    tokens = [t for t in tokens if t not in stopwords and len(t) > 1]

    return tokens


def bm25_rerank(
    docs: List[str],
    metas: List[Dict],
    query_text: str,
    top_n: int
) -> tuple[List[str], List[Dict]]:
    """
    Re-rank documents using BM25 lexical relevance.

    Returns:
        Tuple of (reranked_docs, reranked_metas)
    """
    if not HAS_BM25:
        print("[INFO] BM25 not available; skipping re-ranking.")
        return docs[:top_n], metas[:top_n]

    # Tokenize corpus with domain-specific preprocessing
    tokenized_corpus = [preprocess_for_bm25(d) for d in docs]
    tokenized_query = preprocess_for_bm25(query_text)

    # Compute BM25 scores
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    # Sort by score and take top_n
    idx_sorted = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:top_n]

    reranked_docs = [docs[i] for i in idx_sorted]
    reranked_metas = [metas[i] for i in idx_sorted]

    return reranked_docs, reranked_metas


def hybrid_retrieve(
    collection,
    query_text: str,
    pool_size: int = 100,
    top_k: int = 40,
    where: Optional[dict] = None,
) -> tuple[List[str], List[Dict]]:
    """
    Two-stage hybrid retrieval:
    1. Vector search pulls pool_size candidates
    2. BM25 re-ranks to keep top_k

    Args:
        collection: Chroma collection
        query_text: Search query
        pool_size: Number of candidates from vector search
        top_k: Number to keep after BM25 reranking
        where: Optional metadata filter

    Returns:
        Tuple of (docs, metadatas)
    """
    from .vectordb import query

    # Stage 1: Vector search
    hits = query(collection, query_text, n=pool_size, where=where)

    if not hits or not hits.get("documents") or not hits["documents"][0]:
        print("[WARN] No retrieval hits from vector search.")
        return [], []

    docs = hits["documents"][0]
    metas = hits["metadatas"][0]

    print(f"[INFO] Retrieved {len(docs)} chunks from vector search.")

    # Stage 2: BM25 re-ranking
    if top_k and top_k < len(docs):
        docs, metas = bm25_rerank(docs, metas, query_text, top_n=top_k)
        print(f"[INFO] After BM25 re-ranking: {len(docs)} chunks retained (top_k={top_k}).")
    else:
        print("[INFO] Skipping BM25 re-rank (top_k >= pool_size or disabled).")

    return docs, metas
