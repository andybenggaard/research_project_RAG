# src/embedder_ollama.py
import requests, time
from typing import List
from .config import OLLAMA_HOST, EMBEDDING_MODEL


def _parse_embedding(payload):
    """
    Ollama embeddings response formats:
      - {"embedding": [...]}
      - {"data": [{"embedding": [...]}]}
    """
    if isinstance(payload, dict):
        if "embedding" in payload and payload["embedding"]:
            return payload["embedding"]
        if "data" in payload and payload["data"]:
            emb = payload["data"][0].get("embedding", [])
            if emb:
                return emb
    return None


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts using Ollama's /api/embeddings.

    NOTE: For models like `nomic-embed-text`, the correct field is `prompt`
    (NOT `input`), which is why earlier calls were returning empty embeddings.
    """
    url = f"{OLLAMA_HOST}/api/embeddings"
    out: List[List[float]] = []

    for i, t in enumerate(texts):
        # Use "prompt" instead of "input" (matches the working curl call)
        payload = {
            "model": EMBEDDING_MODEL,
            "prompt": t,
        }
        last_err = None

        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, timeout=60)
                if resp.ok:
                    data = resp.json()
                    emb = _parse_embedding(data)
                    if emb and isinstance(emb, list) and len(emb) > 0:
                        out.append(emb)
                        break
                    last_err = RuntimeError(
                        f"Empty/invalid embedding for item {i}: {data}"
                    )
                else:
                    last_err = RuntimeError(
                        f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except Exception as e:
                last_err = e

            time.sleep(0.6 * (attempt + 1))

        if len(out) < i + 1:
            # hard fail so caller can see the last error
            raise last_err or RuntimeError("Unknown embeddings error")

    return out