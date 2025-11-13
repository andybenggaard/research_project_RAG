import requests, subprocess, shlex
from src.config import OLLAMA_HOST, LLM_MODEL


def _via_generate(system_prompt: str, user_prompt: str) -> str:
    url = f"{OLLAMA_HOST}/api/generate"
    prompt = f"<s>[SYSTEM]\n{system_prompt}\n[/SYSTEM]\n[USER]\n{user_prompt}\n[/USER]"
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},  # deterministic
    }
    r = requests.post(url, json=payload, timeout=120)
    if r.status_code in (404, 405):
        raise FileNotFoundError("generate endpoint not available")
    r.raise_for_status()
    return r.json().get("response", "")


def _via_chat(system_prompt: str, user_prompt: str) -> str:
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0},  # deterministic
    }
    r = requests.post(url, json=payload, timeout=120)
    if r.status_code in (404, 405):
        raise FileNotFoundError("chat endpoint not available")
    r.raise_for_status()
    data = r.json()
    # prefer single 'message' if present
    msg = data.get("message")
    if isinstance(msg, dict):
        return msg.get("content", "")
    # otherwise scan messages
    for m in reversed(data.get("messages", [])):
        if m.get("role") == "assistant":
            return m.get("content", "")
    return ""


def _via_cli(system_prompt: str, user_prompt: str) -> str:
    combined = f"[SYSTEM]\n{system_prompt}\n[/SYSTEM]\n[USER]\n{user_prompt}\n[/USER]"
    cmd = f'ollama run {shlex.quote(LLM_MODEL)} {shlex.quote(combined)}'
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def generate(system_prompt: str, user_prompt: str, stream=False) -> str:
    try:
        return _via_generate(system_prompt, user_prompt)
    except Exception:
        try:
            return _via_chat(system_prompt, user_prompt)
        except Exception:
            return _via_cli(system_prompt, user_prompt)
