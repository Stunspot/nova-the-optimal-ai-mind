#!/usr/bin/env python3
"""Deterministic complete-workflow cost accounting for Cognition Economist."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOKEN_MAP = {
    "input_tokens": "input_per_million",
    "cached_input_read_tokens": "cached_input_read_per_million",
    "cache_write_tokens": "cache_write_per_million",
    "output_tokens": "output_per_million",
    "reasoning_tokens": "reasoning_per_million",
}
UNIT_MAP = {
    "requests": "request_each",
    "tool_calls": "tool_each",
    "search_calls": "search_each",
    "images": "image_each",
    "storage_gb_hours": "storage_gb_hour",
    "infrastructure_hours": "infrastructure_hour",
    "review_hours": "review_hour",
}


class CostError(Exception):
    pass


def load(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CostError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CostError(f"{path} must contain a JSON object")
    return value


def nonnegative(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise CostError(f"{label} must be a non-negative number")
    return float(value)


def estimate(card: dict[str, Any], run: dict[str, Any], allow_incomplete: bool) -> dict[str, Any]:
    if card.get("format") != "cd-cognition-rate-card/v1":
        raise CostError("rate card format must be cd-cognition-rate-card/v1")
    if run.get("format") != "cd-cognition-workflow-run/v1":
        raise CostError("run format must be cd-cognition-workflow-run/v1")
    if card.get("id") != run.get("route_id"):
        raise CostError("rate card id must equal run route_id")
    attempts = int(nonnegative(run.get("attempts"), "attempts"))
    accepted = int(nonnegative(run.get("accepted_outcomes"), "accepted_outcomes"))
    if attempts < 1 or accepted > attempts:
        raise CostError("attempts must be at least one and accepted_outcomes cannot exceed attempts")
    prices = card.get("prices") or {}
    quantities = run.get("quantities") or {}
    components: dict[str, float] = {}
    unknown: list[str] = []
    provider_subtotal = 0.0

    for quantity_name, price_name in TOKEN_MAP.items():
        quantity = nonnegative(quantities.get(quantity_name, 0), quantity_name)
        rate = prices.get(price_name)
        if quantity and rate is None:
            unknown.append(price_name)
            continue
        cost = quantity / 1_000_000 * nonnegative(rate or 0, price_name)
        components[quantity_name] = cost
        provider_subtotal += cost
    for quantity_name, price_name in UNIT_MAP.items():
        quantity = nonnegative(quantities.get(quantity_name, 0), quantity_name)
        rate = prices.get(price_name)
        if quantity and rate is None:
            unknown.append(price_name)
            continue
        cost = quantity * nonnegative(rate or 0, price_name)
        components[quantity_name] = cost
        provider_subtotal += cost

    surcharge = provider_subtotal * nonnegative(card.get("surcharge_percent", 0), "surcharge_percent") / 100
    fixed = nonnegative(card.get("fixed_cost", 0), "fixed_cost")
    components["provider_surcharge"] = surcharge
    components["fixed_cost"] = fixed

    direct = run.get("direct_costs") or {}
    for name, value in direct.items():
        if name == "waste":
            continue
        components[f"direct_{name}"] = nonnegative(value, f"direct_costs.{name}")
    total = sum(components.values())
    if unknown and not allow_incomplete:
        raise CostError("positive quantities have unknown rates: " + ", ".join(sorted(unknown)))
    elapsed = run.get("elapsed_hours")
    elapsed_value = nonnegative(elapsed, "elapsed_hours") if elapsed is not None else None
    waste = nonnegative(direct.get("waste", 0), "direct_costs.waste")
    report = {
        "format": "cd-cognition-cost-report/v1",
        "route_id": run["route_id"],
        "currency": card["currency"],
        "status": "incomplete" if unknown else "complete",
        "components": {key: round(value, 10) for key, value in sorted(components.items())},
        "unknown_components": sorted(set(unknown)),
        "total_cost": round(total, 10),
        "attempts": attempts,
        "accepted_outcomes": accepted,
        "cost_per_attempt": round(total / attempts, 10),
        "cost_per_accepted_outcome": round(total / accepted, 10) if accepted else None,
        "waste_ratio": round(waste / total, 10) if total else None,
        "cost_velocity_per_hour": round(total / elapsed_value, 10) if elapsed_value else None,
        "eligible": bool(run.get("eligible")),
        "floor_failures": list(run.get("floor_failures") or []),
        "evidence": {"rate_card_id": card["id"], "source": card["source"], "mode": run.get("mode"), "assumptions": run.get("assumptions", [])},
    }
    return report


def compare(reports: list[dict[str, Any]]) -> dict[str, Any]:
    currencies = {item.get("currency") for item in reports}
    if len(currencies) != 1:
        raise CostError("all reports must use the same normalized currency")
    eligible = [item for item in reports if item.get("eligible") and item.get("status") == "complete" and item.get("cost_per_accepted_outcome") is not None]
    ranked = sorted(eligible, key=lambda item: (item["cost_per_accepted_outcome"], item["route_id"]))
    return {
        "format": "cd-cognition-route-comparison/v1",
        "currency": next(iter(currencies)),
        "recommended_route": ranked[0]["route_id"] if ranked else None,
        "status": "decision-supported" if ranked else "no-eligible-complete-route",
        "ranked_eligible_routes": [{"route_id": item["route_id"], "cost_per_accepted_outcome": item["cost_per_accepted_outcome"], "total_cost": item["total_cost"]} for item in ranked],
        "excluded_routes": [{"route_id": item.get("route_id"), "reason": "ineligible" if not item.get("eligible") else "incomplete-or-no-accepted-outcome", "floor_failures": item.get("floor_failures", []), "unknown_components": item.get("unknown_components", [])} for item in reports if item not in ranked],
        "boundary": "Arithmetic recommendation only; quality evidence and human route authority remain external."
    }


def emit(value: dict[str, Any], output: str | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    est = sub.add_parser("estimate")
    est.add_argument("--rate-card", required=True); est.add_argument("--run", required=True); est.add_argument("--output")
    est.add_argument("--allow-incomplete", action="store_true")
    comp = sub.add_parser("compare")
    comp.add_argument("reports", nargs="+"); comp.add_argument("--output")
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        if args.command == "estimate":
            emit(estimate(load(args.rate_card), load(args.run), args.allow_incomplete), args.output)
        else:
            emit(compare([load(path) for path in args.reports]), args.output)
        return 0
    except CostError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
