import argparse
from .ingest import ingest_reports
from .extract_facts import extract_facts
from .recursive_verify import verifier
from .vectordb import get_client, get_collection

def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")

    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("--reports", required=True)
    p_ing.add_argument("--db", required=True)

    p_ext = sub.add_parser("extract-facts")
    p_ext.add_argument("--db", required=True)
    p_ext.add_argument("--query", default="Extract Scope 1–3 emissions, units, base year, method, assurance level")
    p_ext.add_argument("--prompt", default="prompts/extract_facts.md")
    p_ext.add_argument("--out", required=True)
    p_ext.add_argument("--company", default="Unknown Co.")
    p_ext.add_argument("--year", type=int, default=2024)

    p_ver = sub.add_parser("verify")
    p_ver.add_argument("--facts", required=True)
    p_ver.add_argument("--db", required=True)
    p_ver.add_argument("--out", required=True)

    args = p.parse_args()
    if args.cmd == "ingest":
        ingest_reports(args.reports, args.db)

    elif args.cmd == "extract-facts":
        extract_facts(args.db, args.query, args.prompt, args.out, args.company, args.year)

    elif args.cmd == "verify":
        import json
        client = get_client(args.db)
        col = get_collection(client)
        facts = json.load(open(args.facts))
        results = []
        for f in facts.get("facts", []):
            statement = f.get("claim") or f.get("metric") or str(f)
            results.append({"statement": statement, "verification": verifier(statement, col)})
        json.dump(results, open(args.out,"w"), indent=2)

if __name__ == "__main__":
    main()
