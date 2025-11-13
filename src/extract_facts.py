import json, re
from .vectordb import get_client, get_collection, query
from .llm_ollama import generate


def extract_facts(db_dir: str, query_text: str, prompt_path: str, out_path: str, company: str, year: int):
    client = get_client(db_dir)
    col = get_collection(client)

    # Collect metadata to find file name for filtering
    all_m = col.get(include=["metadatas"], limit=9999)["metadatas"]
    fname = sorted({m["file_name"] for m in all_m})[0] if all_m else None
    where = {"file_name": {"$eq": fname}} if fname else None

    hits = query(col, query_text, n=30, where=where)

    # --- no-hits safeguard BEFORE touching [0]
    if not hits or not hits.get("documents") or not hits["documents"] or not hits["documents"][0]:
        with open(out_path, "w") as f:
            json.dump({"company": company, "year": year, "facts": [], "raw": "no_hits"}, f, indent=2)
        print(f"[warn] No retrieval hits found. Empty shell saved → {out_path}")
        return

    print(f"[info] Retrieved {len(hits['documents'][0])} chunks from {fname}")
    for i, (doc, meta) in enumerate(zip(hits["documents"][0], hits["metadatas"][0])):
        if i < 3:
            print(f"[ctx {i+1}] p.{meta['page']} len={len(doc)} :: {doc[:160].replace('\\n',' ')}")

    # Build a grounded context block with quotes + metadata
    contexts = []
    for doc, meta in zip(hits["documents"][0], hits["metadatas"][0]):
        snippet = doc[:1600]
        contexts.append(f"[p.{meta['page']} – {meta['file_name']}]\n{snippet}\n")

    with open(prompt_path, "r") as f:
        sys_prompt = f.read().strip()

    user_prompt = f"""Company: {company}
Year: {year}
You are given EVIDENCE (quotes with page refs). Extract facts as per instructions.

EVIDENCE:
{"\n---\n".join(contexts)}
"""

    print(f"[info] Calling LLM…")

    resp = generate(system_prompt=sys_prompt, user_prompt=user_prompt)

    # Robust JSON extraction
    match = re.search(r"\{[\s\S]*\}", resp)
    json_str = match.group(0) if match else "{}"

    try:
        data = json.loads(json_str)
    except Exception:
        data = {"company": company, "year": year, "facts": [], "raw": resp}

    # ensure expected keys
    data.setdefault("company", company)
    data.setdefault("year", year)
    data.setdefault("facts", [])

    # (Optional) simple numeric-fact miner as fallback
    if not data["facts"]:
        mined = _fallback_mine_numeric_facts(contexts)
        if mined:
            data["facts"] = mined
            data["raw"] = "fallback_regex_miner"

    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[✓] Saved structured facts → {out_path}")


# ------- optional fallback miner -------
import re as _re
def _fallback_mine_numeric_facts(contexts, cap=12):
    facts = []
    for block in contexts:
        m = _re.match(r"\[p\.(\d+).*?\]\n", block)
        page = int(m.group(1)) if m else None
        text = block.split("\n", 1)[1] if "\n" in block else block
        for sent in _re.split(r"(?<=[\.\?\!])\s+", text):
            if _re.search(r"\b(2019|2030|2050|GtCO2|tCO2|%)\b", sent) and _re.search(r"\d", sent):
                s = sent.strip()
                if 25 < len(s) < 400:
                    facts.append({"page": page, "text": s, "confidence": "medium"})
                    if len(facts) >= cap:
                        return facts
    return facts
