"""
Utility modules for configuration and shared helpers.
"""

from .config import (
    OLLAMA_HOST,
    EMBEDDING_MODEL,
    LLM_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K,
)

__all__ = [
    "OLLAMA_HOST",
    "EMBEDDING_MODEL",
    "LLM_MODEL",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "TOP_K",
]
