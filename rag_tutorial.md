# Tutorial: From Zero to Extracted Facts

This guide walks you from a fresh clone of this repo to structured `facts.json` files that you can feed into Lean / your compliance logic.

We'll cover:

1. Prerequisites  
2. Cloning the repo & virtual environment  
3. Setting up `.env` (Ollama host + model)  
4. Installing dependencies  
5. Verifying Ollama & models  
6. Adding technical reports (PDFs)  
7. Building the vector database (ingest / "vectorizing the PDFs")  
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
```

If `ollama list` prints something (even an empty list), you're set.

## 2. Clone the repo & create a virtual environment

From whatever folder you keep projects in:

```bash
git clone <YOUR_REPO_URL> research_project_RAG
cd research_project_RAG

python3 -m venv .venv
source .venv/bin/activate
```

You should now see `(.venv)` in your shell prompt.

> **Note:** Every time you open a new terminal and want to use this project:
> ```bash
> cd research_project_RAG
> source .venv/bin/activate
> ```

## 3. Set up .env (Ollama host + model)

The code uses environment variables (via `src/config.py`) to know where Ollama is and which model to call.

Create a file named `.env` in the repo root:

```bash
cat > .env << 'EOF'
# Ollama config
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=llama3:8b

# Optional: silence tokenizers parallelism warnings
TOKENIZERS_PARALLELISM=false
EOF
```

Load it into your shell (current session):

```bash
export $(grep -v '^#' .env | xargs)
```

You can re-run that export anytime after activating `.venv`.

## 4. Install dependencies

From the repo root, with the virtualenv active:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If pip prints warnings about telemetry or similar, that's fine. If it errors out completely, fix that before moving on.

## 5. Verify Ollama & pull the LLM

We assume you're using `llama3:8b` as the local reasoning model.

Pull it (if not already present):

```bash
ollama pull llama3:8b
```

Confirm it exists:

```bash
ollama list
```

You should see a line like:

```
llama3:8b    <some-id>   4.7 GB   <date>
```

Quick API sanity check:

```bash
curl -s http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3:8b","prompt":"say hi","stream":false}'
```

You should get a JSON response with something like `"response":"Hi!"`.

## 6. Add your technical reports (PDFs)

The ingest step will vectorize these PDFs.

Put your report(s) into the `reports/` folder:

```bash
mkdir -p reports
cp /path/to/YourTechnicalReport.pdf reports/
```

**Requirements:**

- It must be a text-based PDF (created from Word/InDesign, not just scanned images).
- File extension should be `.pdf` (lowercase).

Sanity-check what the pipeline will see:

```bash
python - << 'PY'
from pathlib import Path
pdfs = [p for p in Path("reports").rglob("*")
        if p.is_file() and p.suffix.lower()==".pdf"]
print("PDFs detected:", *(str(p) for p in pdfs), sep="\n - ")
PY
```

You should see your report listed, e.g.:

```
PDFs detected:
 - reports/YourTechnicalReport.pdf
```

## 7. Build the vector database ("vectorizing the PDFs")

This step:

- Parses each PDF page.
- Chunks the text.
- Computes embeddings.
- Stores everything in a local Chroma DB at `./data/vectors`.

Run:

```bash
rm -rf ./data/vectors   # optional clean slate
python -m src.cli ingest --reports ./reports --db ./data/vectors
```

You should see:

- A progress bar like `Parsing PDFs: 100%|████...|`
- Possibly some lines like `Failed to send telemetry event ...` (these are harmless).

**Check what got vectorized:**

```bash
python - << 'PY'
from src.vectordb import get_client, get_collection
c = get_client("./data/vectors")
col = get_collection(c)
res = col.get(include=["metadatas"], limit=5)
print({m["file_name"] for m in res["metadatas"]})
PY
```

Expected: a set with your report's filename, e.g.:

```python
{'YourTechnicalReport.pdf'}
```

If this is empty, go back to step 6 and make sure the PDF is in `reports/` and has `.pdf` in lowercase.

## 8. Extract grounded facts with the local LLM

Now we query the vector DB and have the local LLM turn retrieved chunks into structured facts.

### 8.1 Ensure the extraction prompt is set

`prompts/extract_facts.md` should contain instructions like:

```markdown
You are a scientific information extraction assistant.

Return ONLY valid JSON with this exact schema:
{
  "company": "<company name>",
  "year": <year>,
  "facts": [
    { "page": <int>, "text": "<verbatim fact from evidence>", "confidence": "low|medium|high" }
  ]
}

Ground rules:
- Extract ONLY facts that appear verbatim (or nearly verbatim) in the EVIDENCE.
- Prefer quantitative facts: numbers, units, %, GtCO2-eq, °C, years.
- Use the page number from tags like [p.X – file.pdf].
- If a confidence qualifier appears ("high confidence"), use it; otherwise choose low/medium/high.
- If NO facts are found, return:
  { "company": "<company name>", "year": <year>, "facts": [] }

No explanations, no markdown — ONLY the JSON.
```

### 8.2 Run the extraction command

Example for the IPCC Technical Summary:

```bash
mkdir -p data/cache

python -m src.cli extract-facts \
  --db ./data/vectors \
  --query "Find sentences mentioning: 2019 global GHG emissions, GtCO2-eq, sector shares (%), mitigation potential, and any 'high confidence' statements in the Technical Summary." \
  --out ./data/cache/facts.json \
  --company "IPCC AR6 WGIII" \
  --year 2022
```

**What this does:**

- Uses the query text to retrieve the top-N relevant chunks from `./data/vectors`.
- Builds an EVIDENCE block with page references.
- Calls your local `llama3:8b` through Ollama.
- Expects a JSON object with `company`, `year`, and a list of `facts`.

You should see logs such as:

```
[info] Retrieved 30 chunks from YourTechnicalReport.pdf
[ctx 1] p.19 len=... :: ...
[info] Calling LLM…
[✓] Saved structured facts → data/cache/facts.json
```

## 9. Inspect the output

Finally, look at the generated facts:

```bash
python - << 'PY'
import json
d = json.load(open("data/cache/facts.json"))
print("company:", d.get("company"))
print("year:", d.get("year"))
print("facts:", len(d.get("facts", [])))
for f in d.get("facts", [])[:10]:
    print(f)
PY
```

You should see something like:

```
company: IPCC AR6 WGIII
year: 2022
facts: 5
{'page': 19, 'text': 'Global greenhouse gas emissions in 2019 were 59 GtCO2-eq (high confidence).', 'confidence': 'high'}
...
```

---

## Summary

At this point you have:

**PDF → chunks → embeddings → vector DB → grounded facts**

You can now:

- Reuse this pipeline for company sustainability reports (CSRD / ESRS / IFRS).
- Feed `facts.json` into downstream code (e.g. Lean axiom generator) to mathematically reason about compliance.