"""Simple retrieval-k ablation for the design report."""

from __future__ import annotations

import statistics

from rag_pipeline import get_rag

TEST_QUERIES = [
    "PTO notice manager approval",
    "remote work another country security approval",
    "benefits eligibility employment type",
    "expense reimbursement receipt approval",
    "workplace conduct HR escalation",
]


def main() -> None:
    rag = get_rag()
    for k in (2, 4, 6):
        results = [rag.search(query, k=k) for query in TEST_QUERIES]
        average = statistics.mean(len(r) for r in results)
        print(f"k={k}: average retrieved chunks={average:.1f}")
        for query, rows in zip(TEST_QUERIES, results):
            top = rows[0]["document_id"] if rows else "none"
            print(f"  {query}: top={top}")


if __name__ == "__main__":
    main()
