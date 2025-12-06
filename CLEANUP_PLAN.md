# Repository Cleanup Plan

## Core Pipeline (KEEP - Essential)

### 1. Ingestion Pipeline
- `src/ingest.py` - Main ingestion orchestrator
- `src/ingestion/__init__.py`
- `src/ingestion/pdf_parser.py` - Parse PDFs
- `src/ingestion/excel_parser.py` - Parse Excel files
- `src/ingestion/chunker.py` - Chunk documents
- `src/ingestion/embedder.py` - Generate embeddings

### 2. Atomization & Extraction
- `src/extraction/atomization.py` - Core atomization logic
- `src/extraction/multi_step.py` - Multi-step extraction with atomization
- `src/extraction/llm_client.py` - Ollama LLM interface
- `prompts/atomize_queries.md` - Atomizer prompt (simplified for Mistral 8B)
- `prompts/critique_queries.md` - Critic prompt (simplified for Mistral 8B)
- `prompts/extract_factsV2.md` - Company fact extraction
- `prompts/extract_regulations.md` - Regulation extraction

### 3. Retrieval
- `src/retrieval/__init__.py`
- `src/retrieval/hybrid_search.py` - Vector + BM25 hybrid search
- `src/retrieval/query_expansion.py` - 180+ semantic search terms

### 4. Main Scripts
- `extract_multi_step_atomic.py` - **MAIN EXTRACTION SCRIPT**
- `process_atomic_numbers.py` - **PROCESS RESULTS FOR AUDIT**
- `Proofs/audit.py` - Audit verification

### 5. Documentation
- `README.md` - Main readme
- `QUICKSTART_ATOMIZATION.md` - Quick start guide

---

## Files to DELETE (Redundant/Old)

### Root Directory
- ❌ `ATOMIZATION_SUMMARY.md` - Verbose implementation summary (not needed for usage)
- ❌ `README_ATOMIZATION.md` - Duplicate of QUICKSTART (3,500 words, too verbose)
- ❌ `USAGE.md` - Old usage guide (superseded by QUICKSTART)
- ❌ `extract_main.py` - Old extraction script (replaced by extract_multi_step_atomic.py)
- ❌ `extract_multi_step.py` - Old multi-step without atomization (replaced)
- ❌ `extract_numbers.py` - Rejected script (not the right approach)
- ❌ `ingest_main.py` - Old ingestion script (use `python -m src.ingest`)
- ❌ `test_atomization.py` - Test script (dev only, not production)

### src/ingestion/
- ❌ `embedder_old.py` - Old embedder implementation

### src/extraction/
- ❌ `extract_facts.py` - Old single-step extraction (replaced by multi_step.py)

### Other
- ❌ `tests/` - If exists and empty/unused
- ❌ `Proofs/EXTRACTION_ISSUES.md` - Dev notes (not needed)
- ❌ `Proofs/FIX_SUMMARY.md` - Dev notes
- ❌ `Proofs/README_extraction.md` - Dev notes

---

## Production Pipeline (What You Actually Use)

### Step 1: Ingest Documents
```bash
python -m src.ingest
```
Uses:
- src/ingest.py
- src/ingestion/* (pdf_parser, chunker, embedder)

### Step 2: Extract with Atomization
```bash
python extract_multi_step_atomic.py --company "Maersk" --year 2023
```
Uses:
- src/extraction/atomization.py
- src/extraction/multi_step.py
- src/extraction/llm_client.py
- src/retrieval/hybrid_search.py
- src/retrieval/query_expansion.py
- prompts/atomize_queries.md
- prompts/critique_queries.md
- prompts/extract_factsV2.md
- prompts/extract_regulations.md

Output: `data/cache/maersk_atomic_2023.json` (170 facts)

### Step 3: Process for Audit
```bash
python process_atomic_numbers.py --input results/numbers.json
```
Uses:
- process_atomic_numbers.py

Output: Audit variables (Scope 1 total, by gas, by source, energy)

### Step 4: Run Audit
```bash
cd Proofs
python audit.py
```
Uses:
- Proofs/audit.py

---

## Summary

**Keep:** 20 essential files
**Delete:** 10+ redundant files

**After cleanup, your workflow is:**
1. `python -m src.ingest` - Ingest PDFs/Excel
2. `python extract_multi_step_atomic.py --company X --year Y` - Extract with atomization
3. `python process_atomic_numbers.py --input results/numbers.json` - Get audit vars
4. `cd Proofs && python audit.py` - Verify compliance
