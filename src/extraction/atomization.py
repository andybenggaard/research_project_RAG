# src/extraction/atomization.py

"""
Automatic atomization of broad requirements into atomic, answerable queries.

This module implements iterative query refinement:
1. Atomizer LLM: Breaks down broad requirements into atomic queries
2. Validator: Checks atomicity rules programmatically
3. Answerability Probe: Tests if queries can retrieve relevant data
4. Critic LLM: Refines failed queries
5. Loop until all queries are atomic and answerable
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..retrieval import get_client, get_collection, hybrid_retrieve
from .llm_client import generate_json


# ======================================================================
# DATA STRUCTURES
# ======================================================================

class AtomicQuery:
    """Represents a single atomic query with validation metadata."""

    def __init__(
        self,
        query_id: str,
        question: str,
        expected_answer_type: str,
        unit_candidates: List[str],
        scope: str,
        category: str,
        keywords: List[str],
        semantic_hints: List[str],
        validation_rules: Dict[str, bool],
    ):
        self.query_id = query_id
        self.question = question
        self.expected_answer_type = expected_answer_type
        self.unit_candidates = unit_candidates
        self.scope = scope
        self.category = category
        self.keywords = keywords
        self.semantic_hints = semantic_hints
        self.validation_rules = validation_rules

        # Tracking metadata
        self.is_atomic = False
        self.is_answerable = False
        self.validation_errors: List[str] = []
        self.retrieval_score: Optional[float] = None
        self.retrieval_samples: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_id": self.query_id,
            "question": self.question,
            "expected_answer_type": self.expected_answer_type,
            "unit_candidates": self.unit_candidates,
            "scope": self.scope,
            "category": self.category,
            "keywords": self.keywords,
            "semantic_hints": self.semantic_hints,
            "validation_rules": self.validation_rules,
            "is_atomic": self.is_atomic,
            "is_answerable": self.is_answerable,
            "validation_errors": self.validation_errors,
            "retrieval_score": self.retrieval_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AtomicQuery':
        """Create from dictionary."""
        query = cls(
            query_id=data["query_id"],
            question=data["question"],
            expected_answer_type=data["expected_answer_type"],
            unit_candidates=data.get("unit_candidates", []),
            scope=data.get("scope", "Scope 1"),
            category=data["category"],
            keywords=data["keywords"],
            semantic_hints=data["semantic_hints"],
            validation_rules=data.get("validation_rules", {}),
        )
        query.is_atomic = data.get("is_atomic", False)
        query.is_answerable = data.get("is_answerable", False)
        query.validation_errors = data.get("validation_errors", [])
        query.retrieval_score = data.get("retrieval_score")
        return query


# ======================================================================
# VALIDATION LOGIC
# ======================================================================

def validate_atomicity(query: AtomicQuery) -> Tuple[bool, List[str]]:
    """
    Check if a query satisfies atomicity criteria.

    Returns:
        (is_atomic, list_of_errors)
    """
    errors = []

    # Rule 1: Must have non-empty question
    if not query.question or len(query.question.strip()) < 10:
        errors.append("Question is too short or empty")

    # Rule 2: Numeric queries must have unit candidates
    if query.expected_answer_type == "number" and not query.unit_candidates:
        errors.append("Numeric query missing unit_candidates")

    # Rule 3: Must specify time period (check for {{reporting_year}} or specific year)
    has_time = "{{reporting_year}}" in query.question or re.search(r'\b(20\d{2}|year|reporting period)\b', query.question.lower())
    if not has_time and query.validation_rules.get("must_contain_year", True):
        errors.append("Missing time period specification")

    # Rule 4: Must have clear scope (Scope 1 for our use case)
    if query.scope != "Scope 1":
        errors.append("Query must target Scope 1")

    # Rule 5: Must have keywords for BM25 retrieval
    if not query.keywords or len(query.keywords) < 3:
        errors.append("Insufficient keywords (need at least 3 for BM25)")

    # Rule 6: Must have semantic hints for vector search
    if not query.semantic_hints or len(query.semantic_hints) < 2:
        errors.append("Insufficient semantic_hints (need at least 2 for embeddings)")

    # Rule 7: Check for multi-metric indicators (AND, OR, plus, comma-separated metrics)
    multi_metric_patterns = [
        r'\band\b.*\b(emission|consumption|factor|data)',
        r'\bor\b.*\b(emission|consumption|factor|data)',
        r',\s*and\s+',
        r'breakdown.*by.*and.*by',
        r'including.*and.*and',
    ]
    question_lower = query.question.lower()
    for pattern in multi_metric_patterns:
        if re.search(pattern, question_lower):
            errors.append(f"Query appears to combine multiple metrics (pattern: '{pattern}')")
            break

    # Rule 8: Category must be valid
    valid_categories = [
        "total_emissions", "emissions_by_gas", "emissions_by_source",
        "emissions_by_facility", "emission_factor", "energy_consumption",
        "methodology", "boundary", "data_quality", "targets", "verification"
    ]
    if query.category not in valid_categories:
        errors.append(f"Invalid category '{query.category}'")

    is_atomic = len(errors) == 0
    return is_atomic, errors


# ======================================================================
# ANSWERABILITY PROBE
# ======================================================================

def probe_answerability(
    query: AtomicQuery,
    db_dir: str,
    probe_k: int = 5,
    year: Optional[int] = None,
) -> Tuple[bool, float, List[str]]:
    """
    Test if query can retrieve relevant data from vector store.

    Uses hybrid search with small k to check for plausible matches.

    Args:
        query: The atomic query to test
        db_dir: Path to vector database
        probe_k: Number of top results to examine (default: 5)
        year: Optional reporting year to substitute for {{reporting_year}}

    Returns:
        (is_answerable, score, sample_snippets)
    """
    client = get_client(db_dir)
    col = get_collection(client)

    # Build retrieval query from keywords and semantic hints
    # Combine keywords (for BM25) and semantic hints (for embeddings)
    query_text = " ".join(query.keywords) + " " + " ".join(query.semantic_hints)

    # Substitute year placeholder if provided
    if year:
        query_text = query_text.replace("{{reporting_year}}", str(year))

    # Run hybrid search with small pool
    try:
        docs, metas = hybrid_retrieve(
            col,
            query_text=query_text,
            pool_size=20,  # Small pool for probe
            top_k=probe_k,
            where=None,
        )
    except Exception as e:
        print(f"[ERROR] Answerability probe failed for {query.query_id}: {e}")
        return False, 0.0, []

    if not docs:
        return False, 0.0, []

    # Score relevance based on keyword/pattern matching
    score = 0.0
    samples = []

    for doc in docs[:probe_k]:
        doc_lower = doc.lower()
        snippet = doc[:300]  # First 300 chars for sample

        # Check validation rules against retrieved content
        keyword_matches = sum(1 for kw in query.keywords if kw.lower() in doc_lower)

        # For numeric queries, check if doc contains numbers
        if query.validation_rules.get("must_contain_number", False):
            has_number = bool(re.search(r'\d+[,.]?\d*', doc))
            if not has_number:
                continue  # Skip docs without numbers

        # For Scope 1 queries, verify mention
        if query.validation_rules.get("must_mention_scope_1", False):
            has_scope_1 = bool(re.search(r'\bscope\s*1\b|\bdirect\s+emissions?\b', doc_lower))
            if not has_scope_1:
                continue  # Skip docs that don't mention Scope 1

        # For year queries, check year presence (if year provided)
        if query.validation_rules.get("must_contain_year", False) and year:
            has_year = str(year) in doc
            if not has_year:
                continue  # Skip docs without the year

        # Calculate relevance score (simple heuristic)
        relevance = keyword_matches / max(len(query.keywords), 1)
        score += relevance
        samples.append(snippet)

    # Normalize score
    if probe_k > 0:
        score = score / probe_k

    # Threshold: answerable if average relevance > 0.2 and at least 1 sample
    is_answerable = score > 0.2 and len(samples) > 0

    return is_answerable, score, samples


# ======================================================================
# ATOMIZATION PIPELINE
# ======================================================================

def atomize_requirements(
    broad_requirements: List[str],
    atomizer_prompt_path: str,
    critic_prompt_path: str,
    db_dir: str,
    year: Optional[int] = None,
    max_rounds: int = 3,
    probe_answerability_enabled: bool = True,
) -> List[AtomicQuery]:
    """
    Main atomization pipeline: iteratively refine requirements into atomic queries.

    Args:
        broad_requirements: List of broad requirement strings
        atomizer_prompt_path: Path to atomizer prompt
        critic_prompt_path: Path to critic prompt
        db_dir: Path to vector database for answerability probes
        year: Reporting year for substitution
        max_rounds: Maximum refinement iterations
        probe_answerability_enabled: Whether to run answerability probes

    Returns:
        List of validated AtomicQuery objects
    """
    print(f"\n{'='*60}")
    print(f"ATOMIZATION PIPELINE")
    print(f"Requirements: {len(broad_requirements)}")
    print(f"Max rounds: {max_rounds}")
    print(f"Answerability probes: {probe_answerability_enabled}")
    print(f"{'='*60}\n")

    # Load prompts
    with open(atomizer_prompt_path, "r") as f:
        atomizer_prompt = f.read().strip()

    with open(critic_prompt_path, "r") as f:
        critic_prompt = f.read().strip()

    # Stage 1: Initial atomization
    print("[ROUND 1] Initial atomization...")
    all_queries: List[AtomicQuery] = []

    for req_idx, req in enumerate(broad_requirements, start=1):
        user_prompt = f"""
Broad requirement:
\"\"\"{req}\"\"\"

Decompose this requirement into atomic queries following the rules in the system prompt.
Focus on ESRS E1 Scope 1 emissions data.

Return ONLY valid JSON with the 'atomic_queries' array.
"""

        try:
            result = generate_json(
                system_prompt=atomizer_prompt,
                user_prompt=user_prompt,
                max_retries=3,
                temperature=0.1,
            )

            atomic_queries_data = result.get("atomic_queries", [])
            for aq_data in atomic_queries_data:
                query = AtomicQuery.from_dict(aq_data)
                all_queries.append(query)

            print(f"  Requirement {req_idx}: Generated {len(atomic_queries_data)} atomic queries")

        except Exception as e:
            print(f"[ERROR] Failed to atomize requirement {req_idx}: {e}")
            continue

    print(f"[ROUND 1] Total atomic query candidates: {len(all_queries)}")

    # Stage 2: Validation loop
    for round_num in range(1, max_rounds + 1):
        print(f"\n[ROUND {round_num}] Validating {len(all_queries)} queries...")

        validated_queries: List[AtomicQuery] = []
        failed_queries: List[AtomicQuery] = []

        for query in all_queries:
            # Validate atomicity
            is_atomic, errors = validate_atomicity(query)
            query.is_atomic = is_atomic
            query.validation_errors = errors

            if not is_atomic:
                print(f"  ❌ {query.query_id}: Failed atomicity - {errors}")
                failed_queries.append(query)
                continue

            # Optional: Answerability probe
            if probe_answerability_enabled:
                is_answerable, score, samples = probe_answerability(
                    query, db_dir, probe_k=5, year=year
                )
                query.is_answerable = is_answerable
                query.retrieval_score = score
                query.retrieval_samples = samples

                if not is_answerable:
                    print(f"  ⚠️  {query.query_id}: Passed atomicity but failed answerability (score={score:.2f})")
                    query.validation_errors.append(f"Answerability probe failed (score={score:.2f})")
                    failed_queries.append(query)
                    continue
            else:
                query.is_answerable = True  # Skip probe

            # Passed all checks
            print(f"  ✅ {query.query_id}: Atomic and answerable")
            validated_queries.append(query)

        print(f"[ROUND {round_num}] Validated: {len(validated_queries)} | Failed: {len(failed_queries)}")

        # Stage 3: Critic refinement for failed queries
        if not failed_queries or round_num >= max_rounds:
            print(f"[ROUND {round_num}] Stopping (no failures or max rounds reached)")
            all_queries = validated_queries
            break

        print(f"\n[ROUND {round_num}] Running critic on {len(failed_queries)} failed queries...")
        refined_queries: List[AtomicQuery] = []

        for failed_query in failed_queries:
            user_prompt = f"""
Failed Query:
{json.dumps(failed_query.to_dict(), indent=2)}

Failure Reasons:
{json.dumps(failed_query.validation_errors, indent=2)}

Retrieval Context (if probe ran):
Score: {failed_query.retrieval_score}
Sample snippets: {failed_query.retrieval_samples[:2] if failed_query.retrieval_samples else 'N/A'}

Provide critique and refined query candidates.
Return ONLY valid JSON.
"""

            try:
                critique_result = generate_json(
                    system_prompt=critic_prompt,
                    user_prompt=user_prompt,
                    max_retries=3,
                    temperature=0.15,  # Slightly higher for creativity
                )

                refinements = critique_result.get("suggested_refinements", [])
                for ref_data in refinements:
                    refined_query = AtomicQuery.from_dict(ref_data)
                    refined_queries.append(refined_query)

                print(f"  🔧 {failed_query.query_id}: Critic suggested {len(refinements)} refinements")

            except Exception as e:
                print(f"[ERROR] Critic failed for {failed_query.query_id}: {e}")
                continue

        # Next round: validate refined queries + keep validated queries
        all_queries = validated_queries + refined_queries
        print(f"[ROUND {round_num}] Next round will validate {len(all_queries)} queries")

    print(f"\n{'='*60}")
    print(f"[✓] ATOMIZATION COMPLETE")
    print(f"    Final atomic queries: {len(all_queries)}")
    print(f"{'='*60}\n")

    return all_queries


# ======================================================================
# HELPER: Build retrieval query from atomic query
# ======================================================================

def build_retrieval_query(query: AtomicQuery, year: Optional[int] = None) -> str:
    """
    Build a retrieval query string from an AtomicQuery.

    Combines keywords and semantic hints, substitutes year.
    """
    # Weight keywords more heavily for BM25
    query_parts = query.keywords + query.semantic_hints
    query_text = " ".join(query_parts)

    if year:
        query_text = query_text.replace("{{reporting_year}}", str(year))

    return query_text
