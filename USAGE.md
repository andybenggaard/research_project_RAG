# 📖 Usage Guide

This guide shows you how to use your refactored RAG system from the project root.

---

## 🚀 Quick Start

### Prerequisites

1. Activate your virtual environment:
```bash
source .venv/bin/activate
```

2. Ensure environment variables are loaded:
```bash
export $(grep -v '^#' .env | xargs)
```

3. Verify Ollama is running:
```bash
ollama list
```

---

## 📥 Step 1: Ingest PDFs

Convert your PDF reports into vector embeddings.

### Command:
```bash
python ingest_main.py --reports ./reports --db ./data/vectors
```

### What it does:
- Extracts text from PDFs (tables, headings, clean text)
- Chunks documents intelligently (paragraph-aware, section-aware)
- Generates embeddings via Ollama
- Stores in Chroma vector database

### Options:
- `--reports`: Directory containing PDFs (default: `./reports`)
- `--db`: Vector database directory (default: `./data/vectors`)

---

## 📊 Step 2A: Single-Step Extraction (Original Method)

Extract facts in one pass across all documents.

### Command:
```bash
python extract_main.py \
  --db ./data/vectors \
  --out ./data/cache/factsV4.json \
  --company "Maersk" \
  --year 2023 \
  --pool-size 120 \
  --top-k 60
```

### What it does:
1. **Vector search** pulls 120 candidates
2. **BM25 re-ranking** keeps top 60
3. **LLM extraction** processes each chunk
4. **Deduplication** merges similar facts

### Options:
- `--db`: Vector database path
- `--out`: Output JSON file
- `--company`: Company name
- `--year`: Reporting year
- `--pool-size`: Candidates from vector search (default: 100)
- `--top-k`: Keep after BM25 reranking (default: 40)
- `--query`: Custom search query (optional)
- `--prompt`: Custom extraction prompt (default: `prompts/extract_factsV2.md`)

### Output Format:
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
      "file_name": "maersk-sustainability-report-2023.pdf",
      "section_path": "3 Climate > 3.1 Emissions"
    }
  ]
}
```

---

## 🎯 Step 2B: Multi-Step RAG Extraction (NEW! Recommended)

Three-stage pipeline that separates regulation understanding from company data extraction.

### Command:
```bash
python extract_multi_step.py \
  --db ./data/vectors \
  --out ./data/cache/compliance_analysis.json \
  --company "Maersk" \
  --year 2023 \
  --pool-size 120 \
  --top-k 60
```

### What it does:

#### **Stage 1: Extract Regulation Requirements**
- Queries ONLY regulatory documents (ISO 14064, GHG Protocol, ESRS guidance)
- Extracts compliance requirements
- Example: "Companies shall disclose Scope 1 emissions by gas type"

#### **Stage 2: Extract Company Data with Context**
- Uses regulation requirements to build targeted queries
- Queries ONLY company reports for the specified year
- LLM receives regulation context before analyzing company data
- More focused and accurate extraction

#### **Stage 3: Gap Analysis**
- Compares regulation requirements against company disclosures
- Identifies covered requirements
- Identifies missing requirements
- Calculates compliance score

### Options:
- `--db`: Vector database path
- `--out`: Output JSON file
- `--company`: Company name
- `--year`: Reporting year
- `--regulation-prompt`: Regulation extraction prompt (default: `prompts/extract_regulations.md`)
- `--company-prompt`: Company extraction prompt (default: `prompts/extract_factsV2.md`)
- `--pool-size`: Candidates from vector search (default: 100)
- `--top-k`: Keep after BM25 reranking (default: 40)

### Output Format:
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
      "scope": ["Scope 1"],
      "mandatory": true,
      "source_standard": "ESRS E1",
      "source_file": "Overview-Integration-Disclosure-Rules-Jan-2025.pdf",
      "source_page": 12
    }
  ],
  "company_facts": [
    {
      "id": "fact_42_a1b2c3d4e5",
      "page": 42,
      "text": "Maersk's Scope 1 emissions in 2023 were 35.2 million tonnes CO2e",
      "confidence": "high",
      "file_name": "maersk-sustainability-report-2023.pdf"
    }
  ],
  "gap_analysis": {
    "covered_requirements": [
      {
        "requirement": { "requirement_id": "ESRS_E1_R1", "..." },
        "supporting_facts": [ { "id": "fact_42_...", "..." } ]
      }
    ],
    "missing_requirements": [
      {
        "requirement_id": "ESRS_E1_R5",
        "requirement_text": "Shall disclose emission factors used"
      }
    ],
    "compliance_score": 75.5,
    "total_requirements": 20,
    "covered_count": 15,
    "missing_count": 5
  },
  "summary": {
    "total_regulation_requirements": 20,
    "total_company_facts": 45,
    "compliance_score": 75.5,
    "covered_requirements": 15,
    "missing_requirements": 5
  }
}
```

---

## 🔍 Comparison: Single-Step vs Multi-Step

| Aspect | Single-Step | Multi-Step |
|--------|-------------|------------|
| **Speed** | Faster (1 stage) | Slower (3 stages) |
| **Accuracy** | Good | Better (context-aware) |
| **Compliance Analysis** | Manual | Automatic |
| **Use Case** | Quick extraction | Formal compliance verification |
| **Hallucination Risk** | Higher | Lower (grounded in regulations) |
| **Lean Integration** | Manual mapping | Direct mapping |

### When to use Single-Step:
- Quick analysis
- Exploratory data extraction
- Don't need compliance gaps

### When to use Multi-Step:
- Formal compliance verification
- Need gap analysis
- Feeding into Lean proofs
- Auditing purposes

---

## 🛠️ Advanced Options

### Custom Queries

Single-step extraction with custom query:
```bash
python extract_main.py \
  --company "Maersk" \
  --year 2023 \
  --query "Scope 1 emissions methodology calculation factors base year 2019 target 2030"
```

### Custom Prompts

Create your own extraction prompt and use it:
```bash
python extract_main.py \
  --company "Maersk" \
  --year 2023 \
  --prompt prompts/my_custom_prompt.md
```

### Tuning Retrieval

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

---

## 📁 Output Files

### Extraction Output:
- `data/cache/factsV4.json` - Main extraction results
- `data/cache/factsV4.json.partial.jsonl` - Incremental results (JSON Lines format)

### Compliance Analysis Output:
- `data/cache/compliance_analysis.json` - Full multi-step analysis

---

## 🐛 Troubleshooting

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

# Or restart Ollama app
```

### Issue: Empty facts extracted
**Possible causes:**
1. Query doesn't match document content → Refine query
2. Wrong company/year filter → Check file names
3. Vector DB empty → Re-run ingestion

**Debug:**
```bash
# Check what's in vector DB
python -c "
from src.retrieval.vectordb import get_client, get_collection
client = get_client('./data/vectors')
col = get_collection(client)
print(f'Total chunks: {col.count()}')
"
```

---

## 🎓 Examples

### Example 1: Extract Maersk 2023 Data
```bash
# Single-step
python extract_main.py \
  --company "Maersk" \
  --year 2023 \
  --out ./data/cache/maersk_2023.json

# Multi-step
python extract_multi_step.py \
  --company "Maersk" \
  --year 2023 \
  --out ./data/cache/maersk_2023_compliance.json
```

### Example 2: Compare Multiple Years
```bash
# Extract 2022
python extract_main.py --company "Maersk" --year 2022 \
  --out ./data/cache/maersk_2022.json

# Extract 2023
python extract_main.py --company "Maersk" --year 2023 \
  --out ./data/cache/maersk_2023.json

# Compare manually or write comparison script
```

### Example 3: Full Pipeline
```bash
# 1. Ingest all documents
python ingest_main.py

# 2. Extract with multi-step RAG
python extract_multi_step.py \
  --company "Maersk" \
  --year 2023 \
  --out ./data/cache/compliance.json

# 3. View results
python -m json.tool data/cache/compliance.json | less
```

---

## 📚 Next Steps

After extraction, you can:
1. **Validate facts**: Use the validator module
2. **Generate Lean proofs**: Feed into Lean formalization
3. **Create reports**: Build dashboards from JSON
4. **Compare companies**: Extract multiple companies and compare

---

## 🆘 Need Help?

- Check `/docs` for detailed architecture documentation
- Review `/prompts` for prompt templates
- See `/configs` for configuration examples
