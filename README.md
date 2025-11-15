# 🌱 Compliance RAG Starter (Fully Local, Fully Private)

**Target research question** “Can Maersk’s 2030 decarbonization target (e.g. a ~50% improvement in ocean freight carbon intensity and 35% absolute Scope 1 reduction) be verified as fully aligned with ESRS E1-4, which requires companies to set science-based GHG reduction targets for 2030 in their climate transition plans?”
---

## 🎯 What This Does

**Input:** Technical PDF reports (IPCC summaries, CSRD disclosures, sustainability reports)  
**Output:** Structured `facts.json` with page-grounded, verbatim statements

**The Pipeline:**
1. **Ingest** → Parse PDFs with page references
2. **Chunk** → Break into semantic segments
3. **Embed** → Generate vectors using `snowflake-arctic-embed:22m`
4. **Store** → Local Chroma DB (no external dependencies)
5. **Extract** → Query + LLM (`llama3:8b`) → JSON facts
6. **Feed** → Into Lean proofs, compliance checkers, or analytics

**Everything runs offline.** Your data never leaves your machine.

---

## ✨ Key Features

- 🔒 **100% Private** — All processing happens locally via Ollama
- 🚀 **Production-Ready** — Used for CSRD/ESRS compliance extraction
- 📊 **Grounded Facts** — Every fact includes page number + confidence
- 🧩 **Modular** — Swap models, embeddings, or LLMs easily
- 📝 **JSON Output** — Structured data ready for downstream tools
- 🍎 **Apple Silicon Optimized** — Tested on M1/M2/M3 Macs

---

## 📁 Project Structure

```
research_project_RAG/
├── src/
│   ├── cli.py              # Main CLI entry point
│   ├── config.py           # Environment variables + settings
│   ├── ingest.py           # PDF parsing & chunking logic
│   ├── vectordb.py         # Chroma DB interface
│   ├── extract.py          # Fact extraction orchestrator
│   └── llm_client.py       # Ollama API wrapper
├── prompts/
│   └── extract_facts.md    # System prompt for fact extraction
├── reports/                # Drop your PDFs here
├── data/
│   ├── vectors/            # Local Chroma DB (auto-created)
│   └── cache/              # Generated facts.json files
├── requirements.txt        # Python dependencies
├── .env                    # Ollama host + model config
└── README.md               # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **macOS** (tested on Apple Silicon, should work on Intel)
- **Python 3.11+**
- **[Ollama](https://ollama.com/)** installed and running

Verify your setup:

```bash
python3 --version        # Should show 3.11+
ollama list              # Should list models (even if empty)
```

### 1. Clone & Setup Environment

```bash
git clone <YOUR_REPO_URL> compliance-rag
cd compliance-rag

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
```

> 💡 **Tip:** Always activate the venv when working on this project:
> ```bash
> source .venv/bin/activate
> ```

### 2. Configure Environment Variables

Create `.env` in the project root:

```bash
cat > .env << 'EOF'
# Ollama configuration
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3:8b
EMBED_MODEL=snowflake-arctic-embed:22m

# Optional: silence tokenizer warnings
TOKENIZERS_PARALLELISM=false
EOF
```

Load environment variables:

```bash
export $(grep -v '^#' .env | xargs)
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Pull Ollama Models

Download the required models (one-time setup):

```bash
# Embedding model (~22MB)
ollama pull snowflake-arctic-embed:22m

# Reasoning model (~4.7GB)
ollama pull llama3:8b
```

Verify installation:

```bash
ollama list
```

Expected output:
```
NAME                          ID              SIZE
llama3:8b                     a6990ed6be41    4.7 GB
snowflake-arctic-embed:22m    137244915f87    22 MB
```

Quick API test:

```bash
curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3:8b","prompt":"Hello!","stream":false}'
```

You should get a JSON response with `"response":"Hello!..."`.

---

## 📚 Usage Guide

### Step 1: Add Your PDFs

Place technical reports in the `reports/` directory:

```bash
mkdir -p reports
cp /path/to/YourReport.pdf reports/
```

**Requirements:**
- ✅ Text-based PDFs (not scanned images)
- ✅ `.pdf` extension (lowercase)
- ❌ No OCR support yet (coming soon)

Verify your PDFs are detected:

```bash
python - << 'PY'
from pathlib import Path
pdfs = [p for p in Path("reports").rglob("*")
        if p.is_file() and p.suffix.lower()==".pdf"]
print("📄 PDFs detected:")
for p in pdfs:
    print(f"  - {p}")
PY
```

### Step 2: Build Vector Database

This parses PDFs, chunks text, generates embeddings, and stores them locally:

```bash
# Optional: start fresh
rm -rf ./data/vectors

# Ingest PDFs
python -m src.cli ingest \
  --reports ./reports \
  --db ./data/vectors
```

**Expected output:**
```
Parsing PDFs: 100%|████████████████████| 1/1
Chunking pages...
Computing embeddings...
✓ Vectorized 1 document(s) → ./data/vectors
```

**Verify the database:**

```bash
python - << 'PY'
from src.vectordb import get_client, get_collection
client = get_client("./data/vectors")
collection = get_collection(client)
result = collection.get(include=["metadatas"], limit=5)
files = {m["file_name"] for m in result["metadatas"]}
print(f"📊 Indexed files: {files}")
PY
```

### Step 3: Extract Grounded Facts

Query the vector DB and use the LLM to extract structured facts:

```bash
mkdir -p data/cache

python -m src.cli extract-facts \
  --db ./data/vectors \
  --query "Find quantitative statements about GHG emissions, sector shares, mitigation potential, and confidence levels from the Technical Summary." \
  --out ./data/cache/facts.json \
  --company "IPCC AR6 WGIII" \
  --year 2022
```

**What happens:**
1. 🔍 Vector search retrieves top-N relevant chunks
2. 📝 Builds evidence block with page references
3. 🤖 Calls `llama3:8b` with extraction prompt
4. 💾 Saves structured JSON with grounded facts

**Expected logs:**
```
[INFO] Retrieved 30 chunks from YourReport.pdf
[INFO] Building evidence context...
[INFO] Calling LLM for fact extraction...
[✓] Saved structured facts → data/cache/facts.json
```

### Step 4: Inspect Results

```bash
python - << 'PY'
import json

with open("data/cache/facts.json") as f:
    data = json.load(f)

print(f"🏢 Company: {data['company']}")
print(f"📅 Year: {data['year']}")
print(f"📋 Facts extracted: {len(data['facts'])}\n")

for i, fact in enumerate(data['facts'][:5], 1):
    print(f"{i}. Page {fact['page']} [{fact['confidence']}]")
    print(f"   {fact['text']}\n")
PY
```

**Example output:**
```
🏢 Company: IPCC AR6 WGIII
📅 Year: 2022
📋 Facts extracted: 12

1. Page 19 [high]
   Global greenhouse gas emissions in 2019 were 59 GtCO2-eq (high confidence).

2. Page 21 [high]
   Energy supply contributed 34% of global GHG emissions in 2019.

3. Page 23 [medium]
   Mitigation scenarios limit warming to 1.5°C with 50% probability.
```

---

## 🎨 Customization

### Custom Extraction Prompts

Edit `prompts/extract_facts.md` to change how facts are extracted:

```markdown
You are a scientific information extraction assistant.

Return ONLY valid JSON with this exact schema:
{
  "company": "<company name>",
  "year": <year>,
  "facts": [
    {
      "page": <int>,
      "text": "<verbatim fact from evidence>",
      "confidence": "low|medium|high"
    }
  ]
}

Ground rules:
- Extract ONLY facts that appear verbatim in the EVIDENCE
- Prefer quantitative data: numbers, percentages, units
- Use page numbers from [p.X – file.pdf] tags
- Assign confidence based on source language
- Return empty facts array if nothing found

NO explanations. NO markdown. ONLY JSON.
```

### Switch Models

In `.env`, change:

```bash
# For faster extraction (lower quality)
LLM_MODEL=llama3.2:3b

# For better embeddings (larger)
EMBED_MODEL=nomic-embed-text

# For maximum accuracy (slower)
LLM_MODEL=llama3:70b
```

### Adjust Retrieval

In `src/config.py`:

```python
TOP_K = 50              # Number of chunks to retrieve
CHUNK_SIZE = 1000       # Characters per chunk
CHUNK_OVERLAP = 200     # Overlap between chunks
```

---

## 🔧 Troubleshooting

### Issue: "No PDFs detected"

**Solution:**
- Ensure PDFs are in `reports/` directory
- Check file extension is `.pdf` (lowercase)
- Verify PDF is text-based (not scanned image)

### Issue: "Ollama connection refused"

**Solution:**
```bash
# Start Ollama if not running
ollama serve

# Or restart the Ollama app
```

### Issue: "Model not found"

**Solution:**
```bash
ollama pull llama3:8b
ollama pull snowflake-arctic-embed:22m
```

### Issue: Empty `facts.json`

**Possible causes:**
1. Query doesn't match document content → Refine query
2. Prompt too restrictive → Edit `prompts/extract_facts.md`
3. Model hallucinating → Add more context in query
4. Vector DB empty → Re-run `ingest` step

**Debug tips:**
```bash
# Check what's in the vector DB
python - << 'PY'
from src.vectordb import get_client, get_collection
client = get_client("./data/vectors")
collection = get_collection(client)
print(f"Total chunks: {collection.count()}")
PY

# Test retrieval manually
python - << 'PY'
from src.vectordb import get_client, get_collection
client = get_client("./data/vectors")
collection = get_collection(client)
results = collection.query(
    query_texts=["emissions"],
    n_results=3
)
for doc in results['documents'][0]:
    print(doc[:200], "...\n")
PY
```

---

## 🎯 Use Cases

- **🌍 CSRD/ESRS Compliance** — Extract disclosures from sustainability reports
- **📊 Financial Analysis** — Parse technical sections of 10-K filings
- **🔬 Research** — Extract claims from scientific papers
- **⚖️ Legal** — Ground contract facts with page references
- **🏭 ESG Reporting** — Validate emission calculations against standards

---

## 🚦 What's Next?

Once you have `facts.json`:

1. **Feed into Lean** — Generate formal proofs about compliance
2. **Build dashboards** — Visualize facts across multiple reports
3. **Automate checks** — Compare company claims vs. standards
4. **Train models** — Fine-tune on domain-specific extractions
5. **Scale up** — Process hundreds of reports in batch

---

## 📝 Example Workflow

```bash
# 1. Clone and setup
git clone <repo> && cd compliance-rag
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure Ollama
cat > .env << 'EOF'
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3:8b
EMBED_MODEL=snowflake-arctic-embed:22m
EOF

# 3. Pull models
ollama pull llama3:8b
ollama pull snowflake-arctic-embed:22m

# 4. Add PDFs
cp ~/Downloads/*.pdf reports/

# 5. Vectorize
python -m src.cli ingest --reports ./reports --db ./data/vectors

# 6. Extract facts
python -m src.cli extract-facts \
  --db ./data/vectors \
  --query "sustainability metrics carbon emissions scope 1 2 3" \
  --out ./data/cache/facts.json \
  --company "Acme Corp" \
  --year 2023

# 7. Analyze
python -m json.tool data/cache/facts.json
```

---

## 🤝 Contributing

Contributions welcome! Areas of interest:

- [ ] OCR support for scanned PDFs
- [ ] Multi-language document support
- [ ] Batch processing scripts
- [ ] Web UI for fact review
- [ ] Integration with Lean/Coq theorem provers
- [ ] Support for other embedding models

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.com/) — Local LLM inference
- [Chroma](https://www.trychroma.com/) — Vector database
- [LangChain](https://langchain.com/) — Document processing
- [Snowflake Arctic Embed](https://huggingface.co/Snowflake/snowflake-arctic-embed-m) — Embeddings
- [Llama 3](https://llama.meta.com/) — Reasoning model

---

**Ready to extract some facts?** 🚀

```bash
source .venv/bin/activate
python -m src.cli ingest --reports ./reports --db ./data/vectors
```