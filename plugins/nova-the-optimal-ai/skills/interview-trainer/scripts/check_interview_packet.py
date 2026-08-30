#!/usr/bin/env python3
"""Check structural and evidence-state consistency of an interview packet."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

REQUIRED_FILES = (
    "employer-role-brief.md",
    "question-map.csv",
    "evidence-register.csv",
    "answer-bank.md",
    "mock-session-record.md",
    "critique-and-drills.md",
    "questions-to-ask.md",
    "final-interview-brief.md",
    "source-register.md",
)
QUESTION_HEADERS = (
    "question_id", "question_family", "question_text", "role_criterion",
    "probability", "evidence_ids", "practice_priority", "practice_status", "notes",
)
EVIDENCE_HEADERS = (
    "evidence_id", "evidence_summary", "source_ids", "evidence_type",
    "confirmation_state", "notes",
)
SOURCE_HEADERS = (
    "source_id", "source_type", "title_or_identity", "path_or_url",
    "source_date", "retrieved_at", "custody", "use", "notes",
)
PROBABILITIES = {"confirmed", "strongly-indicated", "plausible", "speculative"}
PRIORITIES = {"high", "medium", "low"}
PRACTICE_STATUSES = {"planned", "practiced", "needs-drill", "deferred"}
EVIDENCE_TYPES = {"direct", "adjacent", "user-confirmed"}
CONFIRMATION_STATES = {"confirmed", "confirmation-needed", "unsupported"}
ANSWER_SUPPORT_STATES = {"supported", "confirmation-needed", "honest-gap"}
SESSION_STATES = {"NOT STARTED", "IN PROGRESS", "COMPLETE"}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def split_ids(value: str, pattern: str, label: str, errors: list[str]) -> list[str]:
    items = [item.strip() for item in value.split(";") if item.strip()]
    if len(items) != len(set(items)):
        errors.append(f"{label}: duplicate IDs")
    for item in items:
        if not re.fullmatch(pattern, item):
            errors.append(f"{label}: invalid ID {item!r}")
    return items


def read_csv(path: Path, required: tuple[str, ...], label: str, errors: list[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(reader.fieldnames or ())
        rows = list(reader)
    for name in required:
        if name not in headers:
            errors.append(f"{label} missing header: {name}")
    return rows if all(name in headers for name in required) else []


def answer_section(answer_bank: str, qid: str) -> str | None:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(qid)}\b.*?(?=^##\s+Q-[0-9]{{3}}\b|\Z)",
        answer_bank,
    )
    return match.group(0) if match else None


def field(section: str, name: str) -> str:
    match = re.search(rf"(?im)^-\s*{re.escape(name)}:\s*(.*)$", section)
    return match.group(1).strip() if match else ""


def check(packet: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    if not packet.is_dir():
        return {"ok": False, "errors": [f"not a directory: {packet}"], "warnings": []}

    missing = [name for name in REQUIRED_FILES if not (packet / name).is_file()]
    errors.extend(f"missing required artifact: {name}" for name in missing)
    if missing:
        return {"ok": False, "errors": errors, "warnings": warnings}

    source_rows = read_csv(packet / "source-register.md", SOURCE_HEADERS, "source register", errors)
    sources: dict[str, dict[str, str]] = {}
    for index, row in enumerate(source_rows, start=2):
        sid = (row.get("source_id") or "").strip()
        if not re.fullmatch(r"SRC-[0-9]{3}", sid):
            errors.append(f"source row {index}: invalid source_id {sid!r}")
        elif sid in sources:
            errors.append(f"source row {index}: duplicate source_id {sid}")
        else:
            sources[sid] = row
        for name in ("source_type", "title_or_identity", "custody", "use"):
            if not (row.get(name) or "").strip():
                errors.append(f"source row {index}: missing {name}")

    evidence_rows = read_csv(packet / "evidence-register.csv", EVIDENCE_HEADERS, "evidence register", errors)
    evidence: dict[str, dict[str, object]] = {}
    for index, row in enumerate(evidence_rows, start=2):
        eid = (row.get("evidence_id") or "").strip()
        etype = (row.get("evidence_type") or "").strip().lower()
        confirmation = (row.get("confirmation_state") or "").strip().lower()
        source_ids = split_ids(
            row.get("source_ids") or "", r"SRC-[0-9]{3}",
            f"evidence row {index} source_ids", errors,
        )
        if not re.fullmatch(r"EVD-[0-9]{3}", eid):
            errors.append(f"evidence row {index}: invalid evidence_id {eid!r}")
        elif eid in evidence:
            errors.append(f"evidence row {index}: duplicate evidence_id {eid}")
        if not (row.get("evidence_summary") or "").strip():
            errors.append(f"evidence row {index}: missing evidence_summary")
        if etype not in EVIDENCE_TYPES:
            errors.append(f"evidence row {index}: invalid evidence_type {etype!r}")
        if confirmation not in CONFIRMATION_STATES:
            errors.append(f"evidence row {index}: invalid confirmation_state {confirmation!r}")
        if confirmation == "confirmed" and not source_ids:
            errors.append(f"evidence row {index}: confirmed evidence requires source_ids")
        for sid in source_ids:
            if sid not in sources:
                errors.append(f"evidence row {index}: unknown source_id {sid}")
        if re.fullmatch(r"EVD-[0-9]{3}", eid) and eid not in evidence:
            evidence[eid] = {"row": row, "source_ids": source_ids, "confirmation": confirmation}

    question_rows = read_csv(packet / "question-map.csv", QUESTION_HEADERS, "question map", errors)
    questions: dict[str, dict[str, object]] = {}
    for index, row in enumerate(question_rows, start=2):
        qid = (row.get("question_id") or "").strip()
        probability = (row.get("probability") or "").strip().lower()
        priority = (row.get("practice_priority") or "").strip().lower()
        practice = (row.get("practice_status") or "").strip().lower()
        evidence_ids = split_ids(
            row.get("evidence_ids") or "", r"EVD-[0-9]{3}",
            f"question row {index} evidence_ids", errors,
        )
        if not re.fullmatch(r"Q-[0-9]{3}", qid):
            errors.append(f"question row {index}: invalid question_id {qid!r}")
        elif qid in questions:
            errors.append(f"question row {index}: duplicate question_id {qid}")
        for name in ("question_family", "question_text", "role_criterion"):
            if not (row.get(name) or "").strip():
                errors.append(f"question row {index}: missing {name}")
        if probability not in PROBABILITIES:
            errors.append(f"question row {index}: invalid probability {probability!r}")
        if priority not in PRIORITIES:
            errors.append(f"question row {index}: invalid practice_priority {priority!r}")
        if practice not in PRACTICE_STATUSES:
            errors.append(f"question row {index}: invalid practice_status {practice!r}")
        for eid in evidence_ids:
            if eid not in evidence:
                errors.append(f"question row {index}: unknown evidence_id {eid}")
        if re.fullmatch(r"Q-[0-9]{3}", qid) and qid not in questions:
            questions[qid] = {"row": row, "evidence_ids": evidence_ids, "practice": practice, "priority": priority}

    if not question_rows:
        warnings.append("question map has no rows")

    answer_bank = text(packet / "answer-bank.md")
    for qid, question in questions.items():
        if question["priority"] != "high":
            continue
        section = answer_section(answer_bank, qid)
        if section is None:
            errors.append(f"high-priority {qid} is absent from answer-bank.md")
            continue
        answer_evidence = split_ids(
            field(section, "Evidence IDs"), r"EVD-[0-9]{3}",
            f"answer {qid} evidence IDs", errors,
        )
        if set(answer_evidence) != set(question["evidence_ids"]):
            errors.append(f"answer {qid}: evidence IDs do not match question map")
        support = field(section, "Support state").lower()
        if support not in ANSWER_SUPPORT_STATES:
            errors.append(f"answer {qid}: invalid or missing Support state")
        confirmations = [
            evidence[eid]["confirmation"]
            for eid in answer_evidence
            if eid in evidence
        ]
        if support == "supported" and (not answer_evidence or any(item != "confirmed" for item in confirmations)):
            errors.append(f"answer {qid}: supported state requires confirmed evidence")
        if support == "honest-gap" and answer_evidence:
            errors.append(f"answer {qid}: honest-gap must not cite evidence")

    mock = text(packet / "mock-session-record.md")
    critique = text(packet / "critique-and-drills.md")
    state_match = re.search(r"(?im)^-?\s*Session state:\s*(.+)$", mock)
    session_state = state_match.group(1).strip().upper() if state_match else ""
    if session_state not in SESSION_STATES:
        errors.append(f"mock session has invalid or missing state {session_state!r}")

    observed_qids: set[str] = set()
    if session_state != "NOT STARTED":
        turn_blocks = re.split(r"(?im)^##\s+Turn\s+[0-9]+\s*$", mock)[1:]
        for turn_index, block in enumerate(turn_blocks, start=1):
            qmatch = re.search(r"(?im)^-\s*Question ID:\s*(Q-[0-9]{3})\s*$", block)
            rmatch = re.search(r"(?im)^-\s*User response or accurate summary:\s*(.+)$", block)
            if not qmatch:
                errors.append(f"mock turn {turn_index}: missing stable question ID")
            else:
                qid = qmatch.group(1)
                observed_qids.add(qid)
                if qid not in questions:
                    errors.append(f"mock turn {turn_index}: unknown question ID {qid}")
            if not rmatch or not rmatch.group(1).strip():
                errors.append(f"mock turn {turn_index}: lacks the user's response or accurate summary")
        if not turn_blocks:
            errors.append("recorded mock has no turn records")

    not_observed = "PRACTICE NOT OBSERVED" in critique.upper()
    if session_state == "NOT STARTED" and not not_observed:
        errors.append("mock is not started but critique does not state PRACTICE NOT OBSERVED")
    if session_state in {"IN PROGRESS", "COMPLETE"} and not_observed:
        errors.append("critique says PRACTICE NOT OBSERVED although mock session is recorded")

    for qid, question in questions.items():
        practice = question["practice"]
        if practice in {"practiced", "needs-drill"} and qid not in observed_qids:
            errors.append(f"{qid}: practice_status {practice} lacks a recorded user response")
        if qid in observed_qids and practice not in {"practiced", "needs-drill"}:
            errors.append(f"{qid}: recorded response contradicts practice_status {practice}")

    final_brief = text(packet / "final-interview-brief.md")
    if not re.search(r"(?im)^##\s+Readiness statement\s*$", final_brief):
        errors.append("final-interview-brief.md lacks a Readiness statement section")
    if session_state == "NOT STARTED" and "practice unobserved" not in final_brief.lower():
        errors.append("final brief must state practice unobserved when no mock occurred")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    result = check(args.packet.resolve())
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in result["errors"]:
            print(f"ERROR: {item}")
        for item in result["warnings"]:
            print(f"WARNING: {item}")
        print("PASS" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
