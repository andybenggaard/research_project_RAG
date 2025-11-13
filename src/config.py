import os
from dotenv import load_dotenv
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral:7b-instruct")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1100"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
