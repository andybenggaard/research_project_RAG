import sqlite3
from openai import OpenAI

# Point OpenAI SDK at your local vLLM server
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy-key"  # vLLM ignores this
)

DB_PATH = "compliance.db"   # adjust if needed


def run_sql(query, params=None):
    if params is None:
        params = ()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    # Convert rows to list of dicts for nicer printing
    return [dict(r) for r in rows]

SYSTEM_PROMPT = """
You are an assistant that answers questions about a compliance SQLite database.

The database schema is:
- table: incidents(id, date, region, severity, category, description)
- table: controls(id, name, owner, status, last_reviewed)
- table: actions(id, incident_id, owner, due_date, status, notes)

You are allowed to:
1) Propose safe, read-only SQL queries (SELECT only).
2) Use the results to answer the user's question clearly.

When you need SQL, first respond with:

SQL:
<your SQL here>

Then, after you receive the query result, respond with:

ANSWER:
<your explanation here>
"""

def generate_sql_from_question(question: str) -> str:
    prompt = f"""
User question: {question}

Write a single SQLite SELECT statement (no explanations, no markdown).
Important rules:
- Only SELECT queries
- Use correct column and table names from the schema above
- Limit results to at most 50 rows using LIMIT 50
Return only the SQL query.
"""

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )

    sql = response.choices[0].message.content.strip()
    # Optionally strip surrounding ```sql ... ``` if it does that
    if sql.startswith("```"):
        sql = sql.split("```", 2)[1]
        # remove possible "sql\n"
        sql = sql.replace("sql\n", "").strip()
    return sql

def explain_results(question: str, sql: str, rows):
    rows_text = repr(rows)[:6000]  # avoid sending too much
    prompt = f"""
You generated this SQL for the user question:

Question: {question}
SQL: {sql}

The database returned these rows (as Python list[dict]):
{rows_text}

Explain the answer to the user in plain language.
If there are no rows, explain that nothing was found.
"""

    response = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3-8B-Instruct",
        messages=[
            {"role": "system", "content": "You explain database query results clearly and concisely."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content.strip()

def main():
    print("Compliance DB assistant. Type 'exit' to quit.\n")

    while True:
        question = input("Ask about compliance DB> ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            break

        # 1) Get SQL from LLM
        sql = generate_sql_from_question(question)
        print(f"\n[DEBUG] Proposed SQL:\n{sql}\n")

        # Basic safety: reject non-SELECT
        if not sql.lower().lstrip().startswith("select"):
            print("Refusing to run non-SELECT query. Try again.")
            continue

        try:
            # 2) Run SQL on SQLite
            rows = run_sql(sql)
        except Exception as e:
            print(f"Error running SQL: {e}")
            continue

        # 3) Ask LLM to explain
        answer = explain_results(question, sql, rows)
        print("\nAnswer:\n" + answer + "\n")


if __name__ == "__main__":
    main()