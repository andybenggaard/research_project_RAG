# src/llm_ollama.py

"""
Robust Ollama LLM client with:
- strict JSON mode
- retry + repair strategy
- configurable temperature/max_tokens
- support for system + user prompts
- stable for fact extraction pipelines
"""

import json
import requests
import time
from typing import Dict, Any, Optional, List
from .config import OLLAMA_HOST, LLM_MODEL


# -----------------------------------------------------
# Low-level API call
# -----------------------------------------------------
def _ollama_generate(
    system: str,
    prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """
    Raw call to Ollama generate API with system + user messages.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": LLM_MODEL,
        "system": system,
        "prompt": prompt,
        "temperature": temperature,
        "num_predict": max_tokens,
        "stream": False,
    }

    resp = requests.post(url, json=payload, timeout=180)

    if not resp.ok:
        raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    return data.get("response", "")


# -----------------------------------------------------
# JSON fixing logic
# -----------------------------------------------------
def _extract_json_from_text(text: str) -> Optional[Dict]:
    """
    Attempts to extract JSON from a messy LLM output.
    """
    text = text.strip()

    # First try direct load
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try finding JSON inside text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None

    return None


def _repair_json(output: str) -> Optional[Dict]:
    """
    Attempts to clean common JSON issues.
    """
    repaired = output
    repaired = repaired.replace("\n", " ")
    repaired = repaired.replace("\t", " ")
    repaired = repaired.replace("```json", "").replace("```", "")

    # Remove trailing commas
    repaired = repaired.replace(", }", " }").replace(",]", "]")

    return _extract_json_from_text(repaired)


# -----------------------------------------------------
# High-level "safe generation" with retries
# -----------------------------------------------------
def generate_json(
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 4,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Sends prompt → ensures valid JSON → repairs automatically → retries if needed.
    Used by extract_facts.py and recursive verification.
    """
    last_err = None

    for attempt in range(1, max_retries + 1):

        try:
            raw = _ollama_generate(
                system=system_prompt,
                prompt=user_prompt,
                temperature=temperature,
                max_tokens=4096,
            )

            # Try direct JSON parse
            parsed = _extract_json_from_text(raw)
            if parsed:
                return parsed

            # Try repair
            repaired = _repair_json(raw)
            if repaired:
                return repaired

            last_err = ValueError("Model returned invalid JSON.")
            print(f"[WARN] Invalid JSON on attempt {attempt}: {raw[:200]}")

        except Exception as e:
            last_err = e
            print(f"[ERROR] Ollama failure on attempt {attempt}: {str(e)[:200]}")

        time.sleep(1.2 * attempt)  # exponential backoff

    # If all fails, raise error (extraction pipeline will handle)
    raise last_err or RuntimeError("Unknown LLM JSON error")


# -----------------------------------------------------
# Simple text generation (for debugging)
# -----------------------------------------------------
def generate_text(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """Plain text mode."""
    return _ollama_generate(
        system=system_prompt,
        prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )