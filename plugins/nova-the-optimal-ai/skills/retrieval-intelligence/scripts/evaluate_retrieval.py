#!/usr/bin/env python3
"""Evaluate a Retrieval Intelligence index against inspectable cases."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import rag


def load_cases(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "retrieval-eval-cases-v1":
        raise ValueError("Unsupported retrieval evaluation case schema")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Evaluation cases must be a non-empty list")
    return payload


def citation_is_valid(connection: sqlite3.Connection, result: dict[str, object]) -> bool:
    row = connection.execute(
        """
        SELECT s.path, s.sha256 AS source_sha256, c.start_line, c.end_line,
               c.content_sha256
        FROM chunks c JOIN sources s ON s.id = c.source_id
        WHERE c.id = ?
        """,
        (result.get("chunk_id"),),
    ).fetchone()
    if row is None:
        return False
    expected = {
        "source": row["path"],
        "source_sha256": row["source_sha256"],
        "start_line": int(row["start_line"]),
        "end_line": int(row["end_line"]),
        "content_sha256": row["content_sha256"],
    }
    return all(result.get(key) == value for key, value in expected.items())


def evaluate(db_path: Path, case_path: Path) -> tuple[dict[str, object], bool]:
    specification = load_cases(case_path)
    default_top_k = int(specification.get("top_k", 5))
    default_max_chars = int(specification.get("max_context_chars", 6000))
    if default_top_k < 1 or default_max_chars < 256:
        raise ValueError("top_k must be positive and max_context_chars must be at least 256")

    rows: list[dict[str, object]] = []
    total_relevant = 0
    total_retrieved_relevant = 0
    reciprocal_rank_sum = 0.0
    citation_checks = 0
    valid_citations = 0
    budget_passes = 0

    with closing(rag.connect_existing(db_path)) as connection:
        rag.require_index(connection)
        for raw_case in specification["cases"]:
            if not isinstance(raw_case, dict):
                raise ValueError("Every evaluation case must be an object")
            case_id = str(raw_case.get("id", "")).strip()
            query = str(raw_case.get("query", "")).strip()
            relevant = {str(item) for item in raw_case.get("relevant_sources", [])}
            if not case_id or not query or not relevant:
                raise ValueError("Every case needs id, query, and relevant_sources")
            top_k = int(raw_case.get("top_k", default_top_k))
            max_chars = int(raw_case.get("max_context_chars", default_max_chars))
            result = rag.search_index(db_path, query, top_k=top_k)
            retrieved_sources = [str(item["source"]) for item in result["results"]]
            retrieved_relevant = relevant.intersection(retrieved_sources)
            ranks = [
                index
                for index, source in enumerate(retrieved_sources, start=1)
                if source in relevant
            ]
            reciprocal_rank = 1.0 / min(ranks) if ranks else 0.0
            case_valid = [citation_is_valid(connection, item) for item in result["results"]]
            context = rag.assemble_context(result, max_chars)
            budget_ok = len(context) <= max_chars

            total_relevant += len(relevant)
            total_retrieved_relevant += len(retrieved_relevant)
            reciprocal_rank_sum += reciprocal_rank
            citation_checks += len(case_valid)
            valid_citations += sum(case_valid)
            budget_passes += int(budget_ok)
            rows.append(
                {
                    "id": case_id,
                    "query": query,
                    "top_k": top_k,
                    "relevant_sources": sorted(relevant),
                    "retrieved_sources": retrieved_sources,
                    "retrieved_relevant_sources": sorted(retrieved_relevant),
                    "recall_at_k": len(retrieved_relevant) / len(relevant),
                    "reciprocal_rank": reciprocal_rank,
                    "citation_validity": (sum(case_valid) / len(case_valid)) if case_valid else 1.0,
                    "context_chars": len(context),
                    "context_budget": max_chars,
                    "budget_ok": budget_ok,
                }
            )

    case_count = len(rows)
    recall = total_retrieved_relevant / total_relevant
    mrr = reciprocal_rank_sum / case_count
    citation_validity = valid_citations / citation_checks if citation_checks else 1.0
    budget_adherence = budget_passes / case_count
    thresholds = {
        "minimum_recall_at_k": float(specification.get("minimum_recall_at_k", 1.0)),
        "minimum_mrr": float(specification.get("minimum_mrr", 0.75)),
        "minimum_citation_validity": float(specification.get("minimum_citation_validity", 1.0)),
        "minimum_budget_adherence": float(specification.get("minimum_budget_adherence", 1.0)),
    }
    metrics = {
        "recall_at_k": recall,
        "mean_reciprocal_rank": mrr,
        "citation_validity": citation_validity,
        "budget_adherence": budget_adherence,
    }
    passed = (
        recall >= thresholds["minimum_recall_at_k"]
        and mrr >= thresholds["minimum_mrr"]
        and citation_validity >= thresholds["minimum_citation_validity"]
        and budget_adherence >= thresholds["minimum_budget_adherence"]
    )
    report = {
        "schema": "retrieval-evaluation-report-v1",
        "index": rag.inspect_index(db_path),
        "case_file": str(case_path.resolve()),
        "case_count": case_count,
        "metrics": metrics,
        "thresholds": thresholds,
        "passed": passed,
        "cases": rows,
        "limitations": [
            "Metrics establish retrieval behavior for these cases, not source truth or answer correctness.",
            "Source-level relevance can over-credit a long document; use passage-level cases for consequential corpora.",
        ],
    }
    return report, passed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report, passed = evaluate(args.db, args.cases)
        serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized, encoding="utf-8")
            print(args.output)
        else:
            print(serialized, end="")
        return 0 if passed else 1
    except (OSError, ValueError, RuntimeError, sqlite3.Error, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
