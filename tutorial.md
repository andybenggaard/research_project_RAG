# Tutorial: From Zero to Extracted Facts

This guide walks you from a fresh clone of this repo to structured `facts.json` files that you can feed into Lean / your compliance logic.

We’ll cover:

1. Prerequisites  
2. Cloning the repo & virtual environment  
3. Setting up `.env` (Ollama host + model)  
4. Installing dependencies  
5. Verifying Ollama & models  
6. Adding technical reports (PDFs)  
7. Building the vector database (ingest / “vectorizing the PDFs”)  
8. Extracting grounded facts with the local LLM  
9. Inspecting the output  

---

## 1. Prerequisites

You need:

- **macOS** (tested on Apple Silicon)
- **Python 3.11+**
- **[Ollama](https://ollama.com/)** installed and running (Ollama.app or `ollama serve`)

Check basic tools:

```bash
# Python version
python3 --version

# Ollama is installed and responding
ollama list
If ollama list prints something (even an empty list), you’re set.
