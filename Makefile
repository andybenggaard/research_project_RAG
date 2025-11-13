PY=python

ingest:
	$(PY) -m src.cli ingest --reports ./reports --db ./data/vectors

extract:
	$(PY) -m src.cli extract-facts --db ./data/vectors --out $(FACTS_OUT)

verify:
	$(PY) -m src.cli verify --facts ./data/cache/facts.json --db ./data/vectors --out ./data/cache/verification_tree.json
