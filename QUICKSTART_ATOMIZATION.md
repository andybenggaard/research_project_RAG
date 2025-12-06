# Quick Start: Automatic Atomization for ESRS Scope 1

## What This Does

Automatically converts broad ESRS E1 Scope 1 requirements like:

> "Report Scope 1 emissions breakdown by source and gas type"

Into **atomic, answerable queries** like:

1. "Total Scope 1 GHG emissions in tonnes CO2e for 2023"
2. "Scope 1 emissions from stationary combustion in tonnes CO2e for 2023"
3. "Scope 1 emissions from mobile combustion in tonnes CO2e for 2023"
4. "Scope 1 CO2 emissions in tonnes for 2023"
5. "Scope 1 CH4 emissions in tonnes CO2e for 2023"
... and more

Each atomic query uses targeted retrieval with semantic search to find **specific numbers** from sustainability reports.

---

## Installation

Ensure you have the required dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- `chromadb` - Vector database
- `rank-bm25` - BM25 reranking
- `requests` - Ollama API
- `pypdf` or `pdfplumber` - PDF parsing

---

## Step 1: Ingest Documents

Before extraction, you need to ingest your regulatory documents and company reports into the vector database.

```bash
# Ingest all documents from reports/ directory
python -m src.ingest
```

This creates embeddings in `data/vectors/`.

---

## Step 2: Test Atomization (Optional but Recommended)

Test the atomization system with sample ESRS requirements:

```bash
python test_atomization.py
```

**Output:**
- Console: Summary of atomic queries generated
- File: `data/cache/test_atomic_queries.json` - Full atomic query details

**What to look for:**
- ✅ Atomization ratio: 5-8 queries per requirement
- ✅ Answerability: 80%+ queries should pass probe
- ✅ Categories: Should cover total_emissions, emissions_by_gas, emissions_by_source, etc.

---

## Step 3: Run Extraction with Atomization

Extract ESRS Scope 1 data for a specific company and year:

```bash
python extract_multi_step_atomic.py --company "Maersk" --year 2023
```

**What happens:**

```
STAGE 0: ATOMIZATION
├─ Extract broad requirements from regulatory documents
├─ Atomize into 30-50 atomic queries (iterative refinement)
├─ Validate atomicity (single metric, units, time period)
└─ Test answerability (hybrid search probe)

STAGE 1: EXTRACT REGULATIONS
└─ Extract ESRS E1 Scope 1 requirements from GHG Protocol, ISO 14064, etc.

STAGE 2-ATOMIC: EXTRACT COMPANY DATA
├─ For each atomic query:
│   ├─ Build retrieval query (keywords + semantic hints)
│   ├─ Run hybrid search (vector + BM25)
│   ├─ Extract facts using targeted prompt
│   └─ Tag facts with atomic_query_id
└─ Deduplicate and merge facts

STAGE 3: GAP ANALYSIS
└─ Compare requirements vs. facts, calculate compliance score
```

**Output:**
- File: `data/cache/maersk_atomic_2023.json`
- Contains: Atomic queries, extracted facts, gap analysis

---

## Step 4: Review Results

Open the output JSON file:

```bash
cat data/cache/maersk_atomic_2023.json | jq '.summary'
```

**Example output:**
```json
{
  "total_regulation_requirements": 15,
  "total_atomic_queries": 42,
  "total_company_facts": 87,
  "compliance_score": 78.5,
  "covered_requirements": 12,
  "missing_requirements": 3
}
```

**Review atomic queries:**
```bash
cat data/cache/maersk_atomic_2023.json | jq '.atomization_metadata.atomic_queries[0]'
```

**Review extracted facts:**
```bash
cat data/cache/maersk_atomic_2023.json | jq '.company_facts[] | select(.atomic_query_category == "total_emissions")'
```

---

## Advanced Usage

### Custom Parameters

```bash
python extract_multi_step_atomic.py \
  --company "Shell" \
  --year 2022 \
  --pool-size 80 \              # More retrieval candidates per query
  --top-k 40 \                  # More results after reranking
  --max-rounds 2 \              # Fewer atomization rounds (faster)
  --output results/shell_2022.json
```

### Disable Answerability Probe (Faster)

If you want to skip the retrieval probe step:

```bash
python extract_multi_step_atomic.py \
  --company "Maersk" \
  --year 2023 \
  --no-answerability-probe
```

This generates queries faster but may include unanswerable queries.

### Compare Standard vs. Atomization

Run both pipelines and compare:

```bash
# Standard multi-step (no atomization)
python extract_multi_step.py --company "Maersk" --year 2023 --output standard.json

# With atomization
python extract_multi_step_atomic.py --company "Maersk" --year 2023 --output atomic.json

# Compare fact counts
jq '.summary.total_company_facts' standard.json
jq '.summary.total_company_facts' atomic.json
```

**Expected:** Atomization should extract 2-3x more specific facts.

---

## Understanding the Output

### Atomization Metadata

```json
{
  "atomization_metadata": {
    "total_atomic_queries": 42,
    "atomic_queries": [
      {
        "query_id": "Q001",
        "question": "Total Scope 1 GHG emissions in tonnes CO2e for 2023",
        "category": "total_emissions",
        "keywords": ["Scope 1", "total", "emissions", "GHG", "tCO2e", "2023"],
        "semantic_hints": ["total Scope 1 greenhouse gas emissions", ...],
        "is_atomic": true,
        "is_answerable": true,
        "retrieval_score": 0.85
      }
    ]
  }
}
```

### Tagged Facts

Each extracted fact is tagged with the atomic query that retrieved it:

```json
{
  "text": "Total Scope 1 emissions: 1,234,567 tonnes CO2e (2023)",
  "page": 42,
  "confidence": "high",
  "atomic_query_id": "Q001",
  "atomic_query_category": "total_emissions",
  ...
}
```

---

## Troubleshooting

### Issue: No atomic queries generated

**Error:** `[ERROR] No atomic queries generated`

**Solution:**
1. Check if regulatory documents are in vector DB:
   ```bash
   ls data/vectors/
   ```
2. Check if regulations were extracted (Stage 1 output)
3. Review atomizer prompt: `prompts/atomize_queries.md`

### Issue: Low answerability scores

**Warning:** `⚠️ Q042: Passed atomicity but failed answerability (score=0.15)`

**Causes:**
- Query is too specific for the company's industry (e.g., "aluminum smelting" for maritime company)
- No data available in reports for this metric
- Retrieval parameters too strict

**Solutions:**
1. Review failed queries in output JSON
2. Disable probe for initial run: `--no-answerability-probe`
3. Increase `--pool-size` to 100-120

### Issue: Extraction is slow

**Problem:** Takes 30+ minutes for one company

**Solutions:**
1. Reduce `--max-rounds` to 1 (skip refinement)
2. Disable answerability probe: `--no-answerability-probe`
3. Reduce `--top-k` to 20 (fewer chunks per query)
4. Use standard multi-step for exploratory runs

### Issue: Too many atomic queries

**Output:** 100+ atomic queries generated

**Causes:**
- Critic is splitting queries too aggressively
- Many broad requirements as input

**Solutions:**
1. Set `--max-rounds 1` (no critic refinement)
2. Filter regulation requirements before atomization
3. Review critic prompt for over-splitting

---

## What's Next?

### Analyze Gaps

Find missing requirements:

```bash
jq '.gap_analysis.missing_requirements' data/cache/maersk_atomic_2023.json
```

### Export for Verification

Convert to format for Lean formalization:

```bash
# TODO: Add Lean export script
python export_to_lean.py --input data/cache/maersk_atomic_2023.json
```

### Multi-Year Analysis

Run for multiple years:

```bash
for year in 2021 2022 2023; do
  python extract_multi_step_atomic.py --company "Maersk" --year $year
done
```

### Compare Companies

```bash
for company in "Maersk" "Shell" "BP"; do
  python extract_multi_step_atomic.py --company "$company" --year 2023
done
```

---

## Key Differences from Standard Extraction

| Feature | Standard Multi-Step | **With Atomization** |
|---------|-------------------|------------------|
| Query type | Broad, generic | Atomic, specific |
| Retrieval | One query per stage | 30-50 queries per company |
| Semantic hints | Generic | 180+ category-specific phrases |
| Validation | LLM only | Programmatic + retrieval probe |
| Fact tagging | Generic | Tagged with query ID + category |
| Completeness | ~30-40 facts | ~80-120 facts |
| Best for | Exploratory | Production compliance checking |

---

## Support

For issues or questions:
1. Check [README_ATOMIZATION.md](README_ATOMIZATION.md) for detailed documentation
2. Review test output: `data/cache/test_atomic_queries.json`
3. Examine failed queries in extraction output
