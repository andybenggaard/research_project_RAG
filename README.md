# 🌱 Compliance RAG: Automated ESRS Extraction & Verification

**Research Question:** "Can we automatically extract and verify company sustainability data against ESRS standards using RAG and formal verification?"

---

## 🎯 What This Does

Automatically extracts compliance data from sustainability reports using:
1. **Atomic Query Decomposition** - Breaks broad requirements into specific, answerable queries
2. **Multi-Step RAG** - Iterative extraction with validation and refinement
3. **Hybrid Search** - Vector similarity + BM25 lexical ranking
4. **Physics-Based Validation** - Checks if extracted numbers make physical sense
5. **Audit-Ready Output** - Structured data for formal verification

**Everything runs offline.** Your data never leaves your machine.

---

## ✨ Key Features

- 🔒 **100% Private** — All processing happens locally via Ollama (Mistral 8B)
- 🎯 **Atomic Queries** — Decomposes "Total Scope 1 emissions" into 30-50 specific queries
- 📊 **Automatic Validation** — Flags physically impossible emission factors
- 🧩 **Modular Pipeline** — Ingestion → Atomization → Extraction → Audit
- 📝 **Audit-Ready Output** — Direct integration with formal verification
- 🔍 **Hybrid Search** — Vector + BM25 with 180+ semantic search terms
- 🍎 **Apple Silicon Optimized** — Tested on M1/M2/M3 Macs

---

## 📁 Project Structure

```
research_project_RAG/
├── src/
│   ├── ingest.py                    # Main ingestion orchestrator
│   ├── ingestion/
│   │   ├── pdf_parser.py           # PDF extraction with tables
│   │   ├── excel_parser.py         # Excel extraction
│   │   ├── chunker.py              # ESG-optimized chunking
│   │   └── embedder.py             # Ollama embeddings
│   ├── extraction/
│   │   ├── atomization.py          # ⭐ Atomic query generator
│   │   ├── multi_step.py           # Multi-step RAG pipeline
│   │   └── llm_client.py           # Robust JSON generation
│   └── retrieval/
│       ├── hybrid_search.py        # Vector + BM25 search
│       └── query_expansion.py      # 180+ semantic search terms
├── prompts/
│   ├── atomize_queries.md          # Atomizer prompt (simplified for Mistral 8B)
│   ├── critique_queries.md         # Critic prompt
│   ├── extract_factsV2.md          # Company fact extraction
│   └── extract_regulations.md      # Regulation extraction
├── extract_multi_step_atomic.py    # ⭐ Main extraction script
├── process_atomic_numbers.py       # ⭐ Convert to audit variables
├── Proofs/
│   └── audit.py                    # Formal verification
├── reports/                        # Drop PDFs here
├── data/
│   ├── vectors/                    # Chroma vector DB
│   └── cache/                      # Extracted data
├── requirements.txt
├── .env
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **macOS** (tested on Apple Silicon)
- **Python 3.11+**
- **[Ollama](https://ollama.com/)** installed

Verify your setup:
```bash
python3 --version        # Should show 3.11+
ollama list              # Should show mistral:8b
```

### 1. Setup Environment

```bash
# Clone repository
git clone <YOUR_REPO_URL> compliance-rag
cd compliance-rag

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Ollama

Create `.env`:
```bash
cat > .env << 'EOF'
# Ollama configuration
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=mistral:8b
EMBEDDING_MODEL=nomic-embed-text

# Chunking
CHUNK_SIZE=1100
CHUNK_OVERLAP=150

TOKENIZERS_PARALLELISM=false
EOF
```

Pull models:
```bash
ollama pull nomic-embed-text   # ~140MB embeddings
ollama pull mistral:8b          # ~4.7GB LLM
```

---

## 📚 Usage

### Step 1: Ingest Documents

Place PDFs in `reports/` directory:
```bash
mkdir -p reports
cp /path/to/sustainability-report.pdf reports/
```

Ingest into vector database:
```bash
# Clean slate (if re-ingesting)
rm -rf ./data/vectors

# Ingest all PDFs
python -m src.ingest
```

**Output:**
```
[INFO] Found 16 PDF reports.
Parsing & chunking PDFs: 100%|████████| 16/16
[INFO] Total chunks stored: 3,842
```

---

### Step 2: Extract with Atomic Queries

Extract compliance data for a specific company and year:

```bash
python extract_multi_step_atomic.py --company "Maersk" --year 2023
```

**What happens:**

#### **Stage 0: ATOMIZATION**
```
Extracting broad requirements from regulations...
Atomizing into 30-50 atomic queries...
Validating atomicity (units, time period, keywords)...
Testing answerability with hybrid search...
```

#### **Stage 1: EXTRACT REGULATIONS**
```
Extracting ESRS E1 Scope 1 requirements from standards...
```

#### **Stage 2-ATOMIC: EXTRACT COMPANY DATA**
```
For each atomic query:
  ├─ Build retrieval query (keywords + semantic hints)
  ├─ Run hybrid search (vector + BM25)
  ├─ Extract facts with targeted LLM prompts
  └─ Tag facts with atomic_query_id
```

#### **Stage 3: GAP ANALYSIS**
```
Comparing requirements vs. facts...
Calculating compliance score...
```

**Output:** `data/cache/maersk_atomic_2023.json`

**Example output:**
```json
{
  "company": "Maersk",
  "year": 2023,
  "total_atomic_queries": 42,
  "total_facts_extracted": 170,
  "atomization_metadata": {
    "atomic_queries": [
      {
        "query_id": "Q001",
        "question": "Total Scope 1 GHG emissions in tonnes CO2e for 2023",
        "category": "total_emissions",
        "is_atomic": true,
        "is_answerable": true,
        "retrieval_score": 0.85
      }
    ]
  },
  "company_facts": [...]
}
```

---

### Step 3: Process for Audit

Convert extracted facts into audit variables:

```bash
python process_atomic_numbers.py --input data/cache/maersk_atomic_2023.json
```

**Output:**
```
======================================================================
EXTRACTED AUDIT VARIABLES FOR audit.py
======================================================================

# Company: Maersk
# Year: 2023

TOTAL_SCOPE1_TCO2 = 79462.0

ACTIVITY_MWH = {
    "coal_and_products": 0.00,
    "crude_oil_and_petroleum_products": 112971000.00,
    "natural_gas": 0.00,
    "other_fossil_sources": 0.00,
}

SECTOR = "transport"

======================================================================

SUMMARY:
  ✓ Total Scope 1: 79,462 tCO2e

  ✓ Activity data breakdown (MWh):
    - crude_oil_and_petroleum_products: 112,971,000 MWh (100.0%)
    Total: 112,971,000 MWh (406,696 TJ)

  ✗ Implied EF (0.20 tCO2/TJ) is impossibly low.
     Typical EFs: Natural gas ~56, Oil ~74, Coal ~95.

  LIKELY ISSUES:
    - Emissions and energy data may have different scope boundaries
    - Energy might be global while emissions are regional (e.g., UK SECR)
```

**Debug mode** to see which facts were matched:
```bash
python process_atomic_numbers.py --input results/numbers.json --debug
```

**Output:**
```
DEBUG: FUEL CATEGORY MATCHES
======================================================================

CRUDE_OIL_AND_PETROLEUM_PRODUCTS:
  - 112,971,000 MWh | Page 48 | Fuel oils: 112,971 GWh (2023)
  - 1,000 MWh | Page 2 | Diesel: 1,000 tonnes
```

---

## 🎨 Advanced Usage

### Custom Retrieval Parameters

```bash
python extract_multi_step_atomic.py \
  --company "Shell" \
  --year 2022 \
  --pool-size 80 \         # More candidates per query
  --top-k 40 \             # Keep more after BM25
  --max-rounds 2 \         # Fewer atomization iterations
  --output results/shell_2022.json
```

### Disable Answerability Probe (Faster)

```bash
python extract_multi_step_atomic.py \
  --company "Maersk" \
  --year 2023 \
  --no-answerability-probe
```

### Test Atomization Only

```bash
python test_atomization.py
```

---

## 🔍 How It Works

### 1. Atomic Query Decomposition

**Broad requirement:**
> "Report Scope 1 emissions breakdown by source and gas type"

**Atomized into:**
- Q001: Total Scope 1 GHG emissions in tonnes CO2e for 2023
- Q002: Scope 1 CO2 emissions in tonnes for 2023
- Q003: Scope 1 CH4 emissions in tonnes CO2e for 2023
- Q004: Scope 1 emissions from stationary combustion in tonnes CO2e for 2023
- Q005: Scope 1 emissions from mobile combustion in tonnes CO2e for 2023
- ... (30-50 queries total)

### 2. Iterative Refinement

```
Round 1: Atomizer LLM → 35 queries
         ├─ Validator → 28 pass atomicity
         ├─ Answerability Probe → 22 pass retrieval test
         └─ Critic LLM → Refine 13 failed queries

Round 2: Process refined queries
         ├─ Validator → 32 pass (total)
         └─ Answerability Probe → 30 pass (total)

Round 3: Final refinement
         └─ Output: 42 validated atomic queries
```

### 3. Semantic Search Enhancement

Each atomic query includes:
- **Keywords:** ["Scope 1", "emissions", "GHG", "tCO2e", "2023"]
- **Semantic hints:** ["direct emissions from owned sources", "total Scope 1 GHG", "Scope 1 CO2 equivalent"]

**180+ curated semantic phrases** organized by 20 categories:
- total_emissions, co2_emissions, ch4_emissions, n2o_emissions
- stationary_combustion, mobile_combustion, fugitive_emissions
- natural_gas, diesel_fuel, fuel_oil, coal, biomass
- emission_factors, methodology, reduction_targets

### 4. Physics-Based Validation

Checks if implied emission factor is reasonable:

```python
implied_ef = scope1_total_tco2 / total_activity_tj

if implied_ef < 10 tCO2/TJ:
    STATUS = ERROR  # Impossibly low (typical: 56-95)
elif implied_ef < 40 tCO2/TJ:
    STATUS = WARNING  # Low but possible
elif implied_ef > 150 tCO2/TJ:
    STATUS = WARNING  # Unusually high
else:
    STATUS = OK  # Physically reasonable
```

---

## 📊 Performance

### Extraction Completeness

| Method | Facts Extracted | Coverage |
|--------|-----------------|----------|
| Standard RAG | 30-40 facts | Baseline |
| **Atomic RAG** | **80-120 facts** | **2-3x better** |

### Atomization Ratio

- **Input:** 7 broad ESRS requirements
- **Output:** 35-50 atomic queries
- **Ratio:** ~6 queries per requirement

### Answerability

- **Well-formed queries:** 80-95% pass answerability probe
- **Industry-specific:** May fail if company doesn't have that activity
- **Threshold:** Keyword overlap score > 0.2

### Speed

- **Atomization stage:** 2-5 minutes (LLM calls)
- **Answerability probes:** 1-3 minutes (retrieval)
- **Atomic extraction:** 10-20 minutes (30-50 queries)
- **Total:** ~15-30 minutes per company-year

---

## 🔧 Troubleshooting

### Issue: No atomic queries generated

**Solution:**
```bash
# Check if regulatory documents are in vector DB
ls data/vectors/

# Re-run ingestion if empty
rm -rf data/vectors
python -m src.ingest
```

### Issue: Low answerability scores

**Causes:**
- Query too specific for company's industry
- No data in reports for this metric
- Retrieval parameters too strict

**Solutions:**
```bash
# Disable probe for initial run
python extract_multi_step_atomic.py --company "Maersk" --year 2023 --no-answerability-probe

# Increase pool size
python extract_multi_step_atomic.py --company "Maersk" --year 2023 --pool-size 120
```

### Issue: Extraction is slow

**Solutions:**
```bash
# Reduce refinement rounds
python extract_multi_step_atomic.py --company "Maersk" --year 2023 --max-rounds 1

# Disable answerability probe
python extract_multi_step_atomic.py --company "Maersk" --year 2023 --no-answerability-probe
```

### Issue: Empty ACTIVITY_MWH

**Causes:**
- No energy consumption data in reports
- Atomizer didn't generate energy consumption queries

**Debug:**
```bash
# Check which facts were extracted
python process_atomic_numbers.py --input results/numbers.json --debug

# Look for energy_consumption category
cat results/numbers.json | jq '.facts[] | select(.atomic_query_category == "energy_consumption")'
```

---

## 🎯 Example Workflows

### Workflow 1: Complete Pipeline

```bash
source .venv/bin/activate

# 1. Ingest documents
rm -rf ./data/vectors
python -m src.ingest

# 2. Extract with atomization
python extract_multi_step_atomic.py --company "Maersk" --year 2023

# 3. Process for audit
python process_atomic_numbers.py --input data/cache/maersk_atomic_2023.json

# 4. Copy output to audit.py and run verification
cd Proofs
python audit.py
```

### Workflow 2: Multi-Year Comparison

```bash
for year in 2021 2022 2023; do
  python extract_multi_step_atomic.py --company "Maersk" --year $year
  python process_atomic_numbers.py --input data/cache/maersk_atomic_$year.json
done
```

---

## 📝 Files Reference

### Scripts (Root Directory)

- `extract_multi_step_atomic.py` - **Main extraction script with atomization**
- `process_atomic_numbers.py` - **Convert extracted facts to audit variables**
- `test_atomization.py` - Test atomization with sample requirements

### Source Code (`src/`)

- `src/ingest.py` - Ingestion orchestrator
- `src/extraction/atomization.py` - Atomic query generator & validator
- `src/extraction/multi_step.py` - Multi-step RAG pipeline
- `src/extraction/llm_client.py` - Ollama LLM interface
- `src/retrieval/hybrid_search.py` - Vector + BM25 search
- `src/retrieval/query_expansion.py` - 180+ semantic search terms

### Prompts (`prompts/`)

- `atomize_queries.md` - Atomizer prompt (simplified for Mistral 8B)
- `critique_queries.md` - Critic prompt for query refinement
- `extract_factsV2.md` - Company fact extraction prompt
- `extract_regulations.md` - Regulation extraction prompt

### Documentation

- `README.md` - This file
- `QUICKSTART_ATOMIZATION.md` - Quick start guide
- `CLEANUP_PLAN.md` - Repository cleanup plan

---

## 🤝 Contributing

Areas of interest:
- [ ] Parallel execution of atomic queries (5-10x speedup)
- [ ] Excel/table extraction improvements
- [ ] Multi-company batch processing
- [ ] Web UI for fact review
- [ ] Automated Lean proof generation
- [ ] Additional LLM backends (GPT-4, Claude)

---

## 📄 License

MIT License

---

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.com/) — Local LLM inference
- [Mistral 8B](https://mistral.ai/) — Small, fast LLM optimized for extraction
- [Chroma](https://www.trychroma.com/) — Vector database
- [Nomic Embed](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) — Embeddings
- [Lean 4](https://lean-lang.org/) — Theorem prover for formal verification

---

**Ready to extract compliance data?** 🚀

```bash
source .venv/bin/activate
rm -rf ./data/vectors
python -m src.ingest
python extract_multi_step_atomic.py --company "Maersk" --year 2023
python process_atomic_numbers.py --input data/cache/maersk_atomic_2023.json
```

For detailed usage, see [QUICKSTART_ATOMIZATION.md](QUICKSTART_ATOMIZATION.md).
