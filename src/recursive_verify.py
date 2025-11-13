# Minimal drop-in of your Recursive Verification Framework with RAG hooks
from typing import Dict, Any, List
from .vectordb import get_client, get_collection, query

def is_axiom(statement: str) -> bool:
    axioms = ["1 liter of diesel", "GHG Protocol Scope 2 Guidance 2015"]  # extend with a data table
    return any(a.lower() in statement.lower() for a in axioms)

def has_source(statement: str) -> bool:
    keys = ["according to", "per ", "in accordance with", "verified by", "as defined in"]
    return any(k in statement.lower() for k in keys)

def get_sources_from_rag(collection, statement: str) -> List[Dict]:
    res = query(collection, statement, n=5)
    out = []
    for d, m in zip(res["documents"][0], res["metadatas"][0]):
        out.append({"quote": d[:1200], "meta": m})
    return out

def verifier(statement: str, collection, depth=0, visited=None) -> Dict[str, Any]:
    if visited is None: visited = set()
    if statement in visited:
        return {"credibility": "circular_reference", "proof": None}
    visited.add(statement)

    if is_axiom(statement):
        return {"credibility": "axiom", "proof": statement}

    if has_source(statement):
        sources = get_sources_from_rag(collection, statement)
        results = [verifier(s["quote"], collection, depth+1, visited) for s in sources]
        return {"credibility":"verified_from_source","proof": results}

    # Try cross verification
    cross = get_sources_from_rag(collection, statement)
    if cross:
        sub = verifier(cross[0]["quote"], collection, depth+1, visited)
        if sub["credibility"] in ["verified_from_source","derived","axiom"]:
            return {"credibility":"cross_verified","proof": sub}

    # Derivation gate (placeholder)
    return {"credibility":"unsupported","proof": None}
