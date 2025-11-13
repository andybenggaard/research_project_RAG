# Compliance RAG Starter

End-to-end local pipeline to:
1) Ingest technical reports (PDF),
2) Chunk text with page-aware metadata,
3) Vectorize chunks into a local Chroma DB,
4) Use a **small local LLM** (via Ollama) to extract facts for EU compliance analysis,
5) Plug into a **Recursive Verification Framework** to assess credibility.

> Runs fully local on Mac (Apple Silicon) or an NVIDIA GPU (e.g., RTX 3060).

---

## Quick Start

### 0) Install system prerequisites

- **Python 3.10+**
- **Ollama** (local models & embeddings):
  - macOS: `brew install ollama && ollama serve`
  - Linux/Windows (WSL): see https://ollama.com/download
- Pull a **small instruct LLM** and an **embedding model**:
  ```bash
  ollama pull mistral:7b-instruct   # or llama3.2:3b-instruct (very light)
  ollama pull nomic-embed-text

#Structure
compliance-rag/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ Makefile
├─ reports/                 # ← put your PDFs here (Sustainability/Annual/Audit reports)
│  └─ .gitkeep
├─ data/
│  ├─ vectors/              # chroma DB files
│  └─ cache/                # optional: extracted JSON text/tables
├─ prompts/
│  ├─ extract_facts.md      # fact extraction prompt (LLM)
│  └─ classify_clause.md    # clause mapping prompt (optional)
├─ src/
│  ├─ config.py
│  ├─ utils_pdf.py          # robust PDF/text/table extraction
│  ├─ chunking.py           # hierarchical, page-aware chunking
│  ├─ embedder_ollama.py    # embeddings via Ollama (nomic-embed-text)
│  ├─ vectordb.py           # Chroma wrapper
│  ├─ llm_ollama.py         # small local LLM via Ollama (e.g., mistral / llama3.2)
│  ├─ ingest.py             # end-to-end: PDF -> chunks -> vector DB
│  ├─ extract_facts.py      # retrieve + LLM extraction of quant/qual facts
│  ├─ recursive_verify.py   # your Recursive Verification Framework + RAG hooks
│  └─ cli.py                # simple CLI (ingest, query, extract)
└─ tests/
   └─ test_chunking.py
