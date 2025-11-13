import requests, time
from typing import List
from .config import OLLAMA_HOST, EMBEDDING_MODEL

def _parse_embedding(payload):
    # Ollama formats can be {"embedding":[...]} or {"data":[{"embedding":[...]}]}
    if isinstance(payload, dict):
        if "embedding" in payload and payload["embedding"]:
            return payload["embedding"]
        if "data" in payload and payload["data"]:
            emb = payload["data"][0].get("embedding", [])
            if emb:
                return emb
    return None

def embed_texts(texts: List[str]) -> List[List[float]]:
    url = f"{OLLAMA_HOST}/api/embeddings"
    out = []
    for i, t in enumerate(texts):
        payload = {"model": EMBEDDING_MODEL, "input": t}
        last_err = None
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=60)
                if resp.ok:
                    emb = _parse_embedding(resp.json())
                    if emb and isinstance(emb, list) and len(emb) > 0:
                        out.append(emb)
                        break
                    last_err = RuntimeError(f"Empty/invalid embedding for item {i}")
                else:
                    last_err = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                last_err = e
            time.sleep(0.6 * (attempt + 1))
        if not out or len(out) < i+1:
            # hard fail so caller can fallback
            raise last_err or RuntimeError("Unknown embeddings error")
    return out
