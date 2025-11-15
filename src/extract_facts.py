# src/extract_facts.py

"""
Production-grade fact extraction pipeline using:
- improved vectordb retrieval
- per-chunk extraction with JSON guarantee
- deduplication + ESRS-aligned fact IDs
- stable merged output
"""

import json
import hashlib
from typing import List, Dict, Any

from .vectordb import get_client, get_collection, query
from .llm_ollama import generate_json


# --------------------------------------------
# Helpers
# --------------------------------------------
def _fact_id(text: str, page: int) -> str:
    """Deterministic ID."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return f"fact_{page}_{h}"


def _merge_facts(all_facts: List[Dict]) -> List[Dict]:
    """
    Deduplicate facts by (page, text).
    Keeps highest confidence if duplicates appear.
    """
    merged = {}
    for f in all_facts:
        key = (f["page"], f["text"])
        if key not in merged:
            merged[key] = f
        else:
            # pick higher confidence
            priority = {"low": 1, "medium": 2, "high": 3}
            if priority[f["confidence"]] > priority[merged[key]["confidence"]]:
                merged[key] = f
    return list(merged.values())


# --------------------------------------------
# Main extraction
# --------------------------------------------
def extract_facts(
    db_dir: str,
    query_text: str,
    prompt_path: str,
    out_path: str,
    company: str,
    year: int
):
    """
    Multi-chunk robust extraction pipeline.
    """
    client = get_client(db_dir)
    col = get_collection(client)

    # ------------------------------------------------------------
    # LOAD PROMPT
    # ------------------------------------------------------------
    with open(prompt_path, "r") as f:
        system_prompt = f.read().strip()

    # ------------------------------------------------------------
    # DYNAMIC FILE FILTER (first .pdf encountered)
    # ------------------------------------------------------------
    all_meta = col.get(include=["metadatas"], limit=99999).get("metadatas", [])
    pdf_names = sorted({m["file_name"] for m in all_meta})
    fname = pdf_names[0] if pdf_names else None
    where = {"file_name": {"$eq": fname}} if fname else None

    # ------------------------------------------------------------
    # RETRIEVE CONTEXT CHUNKS
    # ------------------------------------------------------------
    hits = query(col, query_text, n=40, where=where)

    if (
        not hits or
        not hits.get("documents") or
        not hits["documents"] or
        not hits["documents"][0]
    ):
        print("[WARN] No retrieval hits — saving empty facts.")
        json.dump(
            {"company": company, "year": year, "facts": [], "raw": "no_hits"},
            open(out_path, "w"),
            indent=2
        )
        return

    docs = hits["documents"][0]
    metas = hits["metadatas"][0]

    print(f"[INFO] Retrieved {len(docs)} chunks from vector DB for extraction.")

    # ------------------------------------------------------------
    # PROCESS PER CHUNK
    # ------------------------------------------------------------
    all_facts = []

    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        page = meta["page"]
        section_path = meta.get("section_path", "")
        file_name = meta["file_name"]

        # limit chunk length (LLM friendly)
        snippet = doc[:1800]

        user_prompt = f"""
Company: {company}
Year: {year}

The following is EVIDENCE from the report:
[page: {page}, file: {file_name}, section: {section_path}]

EVIDENCE:
\"\"\"
{snippet}
\"\"\"

Extract ONLY the facts according to the extraction rules.
Return ONLY valid JSON.
"""

        print(f"[DEBUG] Extracting from chunk {i}/{len(docs)} page={page}")

        try:
            chunk_result = generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_retries=3,
                temperature=0.1,
            )
        except Exception as e:
            print(f"[ERROR] JSON extraction failed for chunk {i}: {e}")
            continue

        # Validate structure
        chunk_facts = chunk_result.get("facts", [])
        if not isinstance(chunk_facts, list):
            chunk_facts = []

        # Normalize & attach metadata
        for f in chunk_facts:
            f.setdefault("page", page)
            f.setdefault("id", _fact_id(f.get("text", ""), page))
            f.setdefault("file_name", file_name)
            f.setdefault("section_path", section_path)
            all_facts.append(f)

    # ------------------------------------------------------------
    # MERGE & DEDUPLICATE
    # ------------------------------------------------------------
    merged_facts = _merge_facts(all_facts)

    print(f"[INFO] Total extracted facts (raw): {len(all_facts)}")
    print(f"[INFO] After merge/dedupe: {len(merged_facts)}")

    # ------------------------------------------------------------
    # SAVE OUTPUT
    # ------------------------------------------------------------
    out = {
        "company": company,
        "year": year,
        "facts": merged_facts,
    }

    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"[✓] Saved structured facts → {out_path}")
