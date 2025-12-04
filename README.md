# 🌱 Compliance RAG: Multi-Step Extraction for ESRS Verification

**Research Question:** "Can Maersk's 2030 decarbonization target be verified as fully aligned with ESRS E1-4 requirements using automated RAG extraction and formal Lean verification?"

---

## 🎯 What This Does

**Input:** Technical PDF reports (ESRS standards, GHG Protocol, ISO 14064, company sustainability reports)
**Output:** Structured compliance analysis with regulation requirements, company facts, and gap analysis

**The Multi-Step Pipeline:**
1. **Extract Regulations** → Parse ESRS/ISO/GHG Protocol requirements
2. **Extract Company Data** → Extract facts from sustainability reports with regulation context
3. **Gap Analysis** → Automatically identify covered vs. missing requirements
4. **Lean Formalization** → Generate formal proofs for mathematical verification

**Everything runs offline.** Your data never leaves your machine.

---

## ✨ Key Features

- 🔒 **100% Private** — All processing happens locally via Ollama
- 🎯 **Multi-Step RAG** — Learns regulations first, then extracts company data with context
- 📊 **Automatic Compliance Scoring** — 90.9% coverage for Maersk ESRS E1
- 🧩 **Modular Architecture** — Separate ingestion, retrieval, extraction, and verification modules
- 📝 **Structured Output** — JSON facts ready for Lean proofs or dashboards
- 🔍 **Hybrid Search** — Vector similarity + BM25 lexical ranking
- 🍎 **Apple Silicon Optimized** — Tested on M1/M2/M3 Macs

---

## 📁 Project Structure

```
research_project_RAG/
├── src/
│   ├── ingestion/          # PDF parsing, chunking, embeddings
│   │   ├── pdf_parser.py   # Advanced PDF extraction with tables
│   │   ├── chunker.py      # ESG-optimized paragraph-aware chunking
│   │   └── embedder.py     # Ollama embeddings client
│   ├── retrieval/          # Vector DB & hybrid search
│   │   ├── vectordb.py     # Chroma DB interface
│   │   ├── hybrid_search.py # Vector + BM25 re-ranking
│   │   └── query_expansion.py # Domain-specific query expansion
│   ├── extraction/         # Fact extraction (single & multi-step)
│   │   ├── single_step.py  # Original single-pass extraction
│   │   ├── multi_step.py   # NEW: 3-stage RAG with compliance analysis
│   │   ├── validator.py    # Fact validation layer
│   │   └── llm_client.py   # Robust JSON generation
│   ├── utils/              # Configuration
│   │   └── config.py       # Environment variables
│   └── ingest.py           # Ingestion orchestrator
├── prompts/
│   ├── extract_factsV2.md       # Company data extraction prompt
│   └── extract_regulations.md   # Regulation extraction prompt (NEW)
├── Proofs/
│   ├── main.lean           # Simple climate target proof
│   └── mainv2.lean         # Comprehensive ESRS E1 Scope 1 formalization
├── reports/                # Drop your PDFs here
├── data/
│   ├── vectors/            # Chroma DB (auto-created)
│   └── cache/              # Extracted facts
├── ingest_main.py          # Ingestion entry point
├── extract_main.py         # Single-step extraction entry point
├── extract_multi_step.py   # Multi-step extraction entry point (NEW)
├── requirements.txt        # Python dependencies
├── .env                    # Ollama configuration
├── USAGE.md               # Detailed usage guide
└── README.md              # This file
```

---

## 🚀 Quick Start

### Prerequisites

- **macOS** (tested on Apple Silicon, works on Intel)
- **Python 3.11+**
- **[Ollama](https://ollama.com/)** installed and running

Verify your setup:

```bash
python3 --version        # Should show 3.11+
ollama list              # Should list models
```

### 1. Clone & Setup Environment

```bash
git clone <YOUR_REPO_URL> compliance-rag
cd compliance-rag

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

> 💡 **Always activate the venv when working:**
> ```bash
> source .venv/bin/activate
> ```

### 2. Configure Environment

Create `.env` in project root:

```bash
cat > .env << 'EOF'
# Ollama configuration
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3:8b
EMBEDDING_MODEL=nomic-embed-text

# Chunking settings
CHUNK_SIZE=1100
CHUNK_OVERLAP=150

# Optional: silence tokenizer warnings
TOKENIZERS_PARALLELISM=false
EOF
```

### 3. Pull Ollama Models

```bash
# Embedding model (~140MB)
ollama pull nomic-embed-text

# Reasoning model (~4.7GB)
ollama pull llama3:8b

# Verify installation
ollama list
```

---

## 📚 Usage

### Step 1: Add Your PDFs

Place reports in the `reports/` directory:

```bash
mkdir -p reports
cp /path/to/YourReport.pdf reports/
```

**Requirements:**
- ✅ Text-based PDFs (not scanned images)
- ✅ `.pdf` extension (lowercase)
- ❌ No OCR support yet

### Step 2: Ingest PDFs into Vector Database

**⚠️ IMPORTANT:** If re-ingesting, delete the existing vector database first:

```bash
# Remove old vector database (if re-running ingestion)
rm -rf ./data/vectors

# Ingest PDFs
python ingest_main.py --reports ./reports --db ./data/vectors
```

**What it does:**
- Extracts text from PDFs (including tables and headings)
- Chunks documents intelligently (paragraph-aware, section-aware)
- Generates embeddings via Ollama
- Stores in Chroma vector database

**Expected output:**
```
[INFO] Found 16 PDF reports.
Parsing & chunking PDFs: 100%|████████████████████| 16/16
[INFO] Processing maersk-sustainability-report-2023.pdf
[INFO] → 245 chunks produced
[INFO] Upserting batch 1/4...
[INFO] Ingestion complete.
[INFO] Total chunks stored: 3,842
```

### Step 3A: Single-Step Extraction (Fast)

Extract facts in one pass across all documents:

```bash
python extract_main.py \
  --db ./data/vectors \
  --out ./data/cache/maersk_facts.json \
  --company "Maersk" \
  --year 2023 \
  --pool-size 120 \
  --top-k 60
```

**Output:** `maersk_facts.json`
```json
{
  "company": "Maersk",
  "year": 2023,
  "facts": [
    {
      "id": "fact_42_a1b2c3d4e5",
      "page": 42,
      "text": "Maersk's Scope 1 emissions in 2023 were 35.2 million tonnes CO2e",
      "confidence": "high",
      "file_name": "maersk-sustainability-report-2023.pdf"
    }
  ]
}
```

### Step 3B: Multi-Step RAG Extraction (Recommended) 🆕

Three-stage pipeline with automatic compliance analysis:

```bash
python extract_multi_step.py \
  --db ./data/vectors \
  --out ./data/cache/compliance_analysis.json \
  --company "Maersk" \
  --year 2023 \
  --pool-size 120 \
  --top-k 60
```

**What it does:**

#### **Stage 1: Extract Regulation Requirements**
- Queries regulatory documents (ISO 14064, GHG Protocol, ESRS)
- Extracts compliance requirements
- Example: "Companies shall disclose Scope 1 emissions by gas type"

#### **Stage 2: Extract Company Data with Context**
- Uses regulation requirements to build targeted queries
- LLM receives regulation context before analyzing company data
- More focused and accurate extraction

#### **Stage 3: Automatic Gap Analysis**
- Compares requirements vs. company disclosures
- Identifies covered and missing requirements
- Calculates compliance score

**Expected output:**
```
============================================================
MULTI-STEP RAG EXTRACTION
Company: Maersk | Year: 2023
============================================================

[STEP 1] Extracting regulation requirements...
[INFO] Retrieved 80 chunks from vector search.
[INFO] After BM25 re-ranking: 30 chunks retained
[STEP 1] ✓ Extracted 99 requirements

[STEP 2] Extracting company data for Maersk (2023)...
[INFO] Retrieved 120 chunks from vector search.
[INFO] After BM25 re-ranking: 60 chunks retained
[STEP 2] ✓ Extracted 125 company facts

[STEP 3] Performing gap analysis...
[STEP 3] ✓ Compliance score: 90.9%
[STEP 3]   Covered: 90 requirements
[STEP 3]   Missing: 9 requirements

============================================================
[✓] Multi-step extraction complete → compliance_analysis.json
============================================================
```

**Output:** `compliance_analysis.json`
```json
{
  "company": "Maersk",
  "year": 2023,
  "extraction_method": "multi_step_rag",
  "regulation_requirements": [
    {
      "requirement_id": "ESRS_E1_R1",
      "requirement_text": "Shall disclose Scope 1 emissions in tCO2e",
      "category": "data_reporting",
      "mandatory": true,
      "source_standard": "ESRS E1"
    }
  ],
  "company_facts": [
    {
      "id": "fact_42_a1b2c3d4e5",
      "page": 42,
      "text": "Maersk's Scope 1 emissions in 2023 were 35.2 million tonnes CO2e",
      "confidence": "high"
    }
  ],
  "gap_analysis": {
    "compliance_score": 90.9,
    "covered_requirements": 90,
    "missing_requirements": 9
  }
}
```

### Extract Company Facts Only

```bash
python3 -c "
import json
with open('data/cache/compliance_analysis.json', 'r') as f:
    data = json.load(f)

output = {
    'company': data['company'],
    'year': data['year'],
    'facts': data['company_facts']
}

with open('data/cache/maersk_facts_only.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'Extracted {len(data[\"company_facts\"])} facts')
"
```

---

## 🔍 Comparison: Single-Step vs Multi-Step

| Aspect | Single-Step | Multi-Step RAG |
|--------|-------------|----------------|
| **Speed** | Faster (1 stage) | Slower (3 stages) |
| **Accuracy** | Good | Better (context-aware) |
| **Compliance Analysis** | Manual | Automatic |
| **Gap Identification** | ❌ No | ✅ Yes |
| **Use Case** | Quick extraction | Formal verification |
| **Hallucination Risk** | Higher | Lower (grounded) |
| **Lean Integration** | Manual | Direct mapping |

**When to use Single-Step:**
- Quick exploratory analysis
- Don't need compliance gaps
- Testing prompts

**When to use Multi-Step:**
- Formal compliance verification ⭐
- Auditing purposes
- Feeding into Lean proofs
- Production use cases

---

## 🎨 Advanced Usage

### Custom Retrieval Tuning

Increase recall (find more candidates):
```bash
python extract_main.py \
  --company "Maersk" \
  --year 2023 \
  --pool-size 200 \
  --top-k 80
```

Increase precision (keep only best):
```bash
python extract_main.py \
  --company "Maersk" \
  --year 2023 \
  --pool-size 80 \
  --top-k 20
```

### Custom Prompts

```bash
python extract_main.py \
  --company "Maersk" \
  --year 2023 \
  --prompt prompts/my_custom_prompt.md
```

### Custom Queries

```bash
python extract_main.py \
  --company "Maersk" \
  --year 2023 \
  --query "Scope 1 emissions methodology calculation factors base year 2019"
```

---

## 🔧 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'dotenv'"

**Solution:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Ollama connection refused"

**Solution:**
```bash
# Start Ollama
ollama serve

# Or restart the Ollama app
```

### Issue: Ingestion fails with "collection already exists"

**Solution:**
```bash
# Delete old vector database before re-ingesting
rm -rf ./data/vectors

# Then run ingestion again
python ingest_main.py --reports ./reports --db ./data/vectors
```

### Issue: Empty facts extracted

**Possible causes:**
1. Query doesn't match document content → Refine query
2. Wrong company/year filter → Check file names
3. Vector DB empty → Re-run ingestion

**Debug:**
```bash
# Check what's in vector DB
python3 -c "
from src.retrieval.vectordb import get_client, get_collection
client = get_client('./data/vectors')
col = get_collection(client)
print(f'Total chunks: {col.count()}')
"
```

---

## 🎯 Example Workflows

### Workflow 1: Complete Pipeline

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Clean slate
rm -rf ./data/vectors

# 3. Ingest all documents
python ingest_main.py

# 4. Multi-step extraction with compliance analysis
python extract_multi_step.py \
  --company "Maersk" \
  --year 2023 \
  --out ./data/cache/compliance.json

# 5. Extract just company facts
python3 -c "
import json
with open('data/cache/compliance.json', 'r') as f:
    data = json.load(f)
output = {'company': data['company'], 'year': data['year'], 'facts': data['company_facts']}
with open('data/cache/maersk_facts_only.json', 'w') as f:
    json.dump(output, f, indent=2)
"

# 6. View results
python -m json.tool data/cache/maersk_facts_only.json | less
```

### Workflow 2: Compare Multiple Years

```bash
# Extract 2021
python extract_multi_step.py --company "Maersk" --year 2021 \
  --out ./data/cache/maersk_2021_compliance.json

# Extract 2023
python extract_multi_step.py --company "Maersk" --year 2023 \
  --out ./data/cache/maersk_2023_compliance.json

# Compare compliance scores
python3 -c "
import json
for year in [2021, 2023]:
    with open(f'data/cache/maersk_{year}_compliance.json', 'r') as f:
        data = json.load(f)
        score = data['gap_analysis']['compliance_score']
        print(f'{year}: {score:.1f}% compliant')
"
```

---

## 📊 Real Results

**Maersk 2023 Multi-Step RAG Extraction:**
- ✅ **99 regulation requirements** extracted from ESRS/ISO/GHG Protocol
- ✅ **125 company facts** extracted from Maersk reports
- ✅ **90.9% compliance score** (90/99 requirements covered)
- ✅ **9 missing requirements** identified for remediation

**Example Missing Requirement:**
> "Shall disclose emission factors used for each significant emission source"

**Example Covered Requirement:**
> "Shall disclose Scope 1 emissions in metric tonnes CO2e" ✓
> Supporting fact: "Maersk's Scope 1 emissions in 2023 were 35.2 million tonnes CO2e"

---

## 🚦 What's Next?

Once you have extracted facts:

1. **Validate Facts** → Use the validator module to check consistency
2. **Generate Lean Proofs** → Feed into `Proofs/mainv2.lean` for formal verification
3. **Build Dashboards** → Visualize compliance across multiple reports
4. **Automate Audits** → Compare company claims vs. standards
5. **Train Models** → Fine-tune on domain-specific extractions

---

## 📝 Files Reference

### Input Files
- `reports/*.pdf` - Your PDF documents

### Output Files
- `data/vectors/` - Vector database (Chroma)
- `data/cache/compliance_analysis.json` - Multi-step extraction results
- `data/cache/maersk_facts_only.json` - Company facts only
- `data/cache/*.partial.jsonl` - Incremental extraction preview

### Configuration Files
- `.env` - Ollama and model configuration
- `prompts/extract_factsV2.md` - Company data extraction prompt
- `prompts/extract_regulations.md` - Regulation extraction prompt

### Documentation
- `README.md` - This file
- `USAGE.md` - Detailed usage examples
- `Proofs/mainv2.lean` - ESRS E1 formal specification

---

## 🤝 Contributing

Contributions welcome! Areas of interest:

- [ ] OCR support for scanned PDFs
- [ ] Multi-language document support
- [ ] Batch processing for multiple companies
- [ ] Web UI for fact review
- [ ] Automated Lean proof generation
- [ ] Additional embedding models

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.com/) — Local LLM inference
- [Chroma](https://www.trychroma.com/) — Vector database
- [Llama 3](https://llama.meta.com/) — Reasoning model
- [Nomic Embed](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) — Embeddings
- [Lean 4](https://lean-lang.org/) — Theorem prover

---

**Ready to verify compliance?** 🚀

```bash
source .venv/bin/activate
rm -rf ./data/vectors  # Clean slate
python ingest_main.py   # Ingest PDFs
python extract_multi_step.py --company "Maersk" --year 2023  # Extract & analyze
```

For detailed examples and troubleshooting, see [USAGE.md](USAGE.md).
