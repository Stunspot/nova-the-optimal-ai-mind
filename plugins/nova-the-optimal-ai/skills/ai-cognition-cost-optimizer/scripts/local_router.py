#!/usr/bin/env python3
"""Plan and execute evidence-gated requests against a local Ollama runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


class RouteError(Exception):
    pass


def load(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RouteError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RouteError(f"{path} must contain a JSON object")
    return value


def emit(value: dict[str, Any], output: str | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if output:
        Path(output).write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")


def local_endpoint(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS:
        raise RouteError("v0.2 local execution permits only an http Ollama endpoint on localhost, 127.0.0.1, or ::1")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RouteError("local endpoint cannot contain credentials, a query, or a fragment")
    if parsed.path not in {"", "/"}:
        raise RouteError("local endpoint must not include an API path")
    try:
        port = parsed.port or 11434
    except ValueError as exc:
        raise RouteError(f"invalid local endpoint port: {exc}") from exc
    host = f"[{parsed.hostname}]" if ":" in (parsed.hostname or "") else parsed.hostname
    return f"http://{host}:{port}"


def request_json(endpoint: str, path: str, payload: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    base = local_endpoint(endpoint)
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base + path,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RouteError(f"local Ollama request failed: {exc}") from exc
    if not isinstance(value, dict):
        raise RouteError("local Ollama response must be a JSON object")
    return value


def inventory(endpoint: str, timeout: float = 10.0) -> dict[str, Any]:
    value = request_json(endpoint, "/api/tags", None, timeout)
    models = []
    for item in value.get("models") or []:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        models.append(
            {
                "name": item["name"],
                "size_bytes": item.get("size"),
                "modified_at": item.get("modified_at"),
                "digest": item.get("digest"),
                "details": item.get("details") or {},
            }
        )
    return {
        "format": "cd-local-model-inventory/v1",
        "endpoint": local_endpoint(endpoint),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "models": sorted(models, key=lambda item: item["name"]),
        "boundary": "Installed inventory only; presence is not quality, capability, privacy, latency, or reliability evidence.",
    }


def required_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise RouteError(f"{label} must be a non-negative number")
    return float(value)


def request_hash(request: dict[str, Any]) -> str:
    encoded = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def candidate_failures(candidate: dict[str, Any], request: dict[str, Any], installed: set[str]) -> list[str]:
    failures: list[str] = []
    model = candidate.get("model")
    if not isinstance(model, str) or not model:
        return ["candidate model is missing"]
    if not candidate.get("enabled", True):
        failures.append("candidate is disabled")
    if model not in installed:
        failures.append("model is not present in the observed local inventory")
    try:
        local_endpoint(candidate.get("endpoint", "http://127.0.0.1:11434"))
    except RouteError as exc:
        failures.append(str(exc))

    qualification = candidate.get("qualification") or {}
    if qualification.get("status") != "qualified":
        failures.append("model is not qualified")
    task_class = request.get("task_class")
    if task_class not in (qualification.get("evaluated_task_classes") or []):
        failures.append("task class lacks qualification evidence")

    required = request.get("required") or {}
    capabilities = candidate.get("capabilities") or {}
    min_context = required_number(required.get("min_context_tokens", 0), "required.min_context_tokens")
    context = capabilities.get("context_tokens")
    if min_context and (not isinstance(context, (int, float)) or context < min_context):
        failures.append("context floor not met")
    required_modalities = set(required.get("modalities") or ["text"])
    candidate_modalities = set(capabilities.get("modalities") or [])
    if not required_modalities.issubset(candidate_modalities):
        failures.append("modality floor not met")
    if required.get("tool_use"):
        failures.append("tool use is outside the v0.2 local executor")
    if required.get("structured_output") and not capabilities.get("structured_output"):
        failures.append("structured-output floor not met")

    min_acceptance = required.get("min_acceptance_rate")
    if min_acceptance is not None:
        threshold = required_number(min_acceptance, "required.min_acceptance_rate")
        observed = qualification.get("acceptance_rate")
        if not isinstance(observed, (int, float)) or observed < threshold:
            failures.append("acceptance-rate floor not met")
    min_reliability = required.get("min_reliability_rate")
    if min_reliability is not None:
        threshold = required_number(min_reliability, "required.min_reliability_rate")
        observed = qualification.get("reliability_rate")
        if not isinstance(observed, (int, float)) or observed < threshold:
            failures.append("reliability floor not met")
    max_latency = required.get("max_p95_latency_ms")
    if max_latency is not None:
        threshold = required_number(max_latency, "required.max_p95_latency_ms")
        observed = qualification.get("observed_p95_latency_ms")
        if not isinstance(observed, (int, float)) or observed > threshold:
            failures.append("latency floor not met")
    max_cost = required.get("max_cost_per_accepted_outcome")
    if max_cost is not None:
        threshold = required_number(max_cost, "required.max_cost_per_accepted_outcome")
        estimated = candidate.get("estimated_cost_per_accepted_outcome")
        if not isinstance(estimated, (int, float)) or estimated > threshold:
            failures.append("cost-per-accepted-outcome floor not met")
    return failures


def plan(policy: dict[str, Any], request: dict[str, Any], inventory_value: dict[str, Any]) -> dict[str, Any]:
    if policy.get("format") != "cd-local-route-policy/v1":
        raise RouteError("policy format must be cd-local-route-policy/v1")
    if request.get("format") != "cd-local-cognition-request/v1":
        raise RouteError("request format must be cd-local-cognition-request/v1")
    if not isinstance(request.get("prompt"), str) or not request["prompt"].strip():
        raise RouteError("request prompt must be a non-empty string")
    if not isinstance(request.get("task_class"), str) or not request["task_class"]:
        raise RouteError("request task_class must be a non-empty string")
    installed = {item.get("name") for item in inventory_value.get("models") or [] if isinstance(item, dict)}
    candidates = []
    for candidate in policy.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        failures = candidate_failures(candidate, request, installed)
        estimated = candidate.get("estimated_cost_per_accepted_outcome")
        if estimated is not None:
            estimated = required_number(estimated, "candidate.estimated_cost_per_accepted_outcome")
        priority = candidate.get("priority", 100)
        priority = required_number(priority, "candidate.priority")
        candidates.append(
            {
                "model": candidate.get("model"),
                "endpoint": candidate.get("endpoint", "http://127.0.0.1:11434"),
                "eligible": not failures,
                "floor_failures": failures,
                "priority": priority,
                "estimated_cost_per_accepted_outcome": estimated,
                "qualification": candidate.get("qualification") or {},
                "options": candidate.get("options") or {},
                "think": candidate.get("think"),
            }
        )
    eligible = [item for item in candidates if item["eligible"]]
    blockers: list[str] = []
    if len(eligible) > 1 and any(item["estimated_cost_per_accepted_outcome"] is None for item in eligible):
        selected = None
        selection_basis = None
        blockers.append("multiple eligible routes cannot be ranked because cost per accepted outcome is unknown")
    else:
        eligible.sort(
            key=lambda item: (
                item["estimated_cost_per_accepted_outcome"]
                if item["estimated_cost_per_accepted_outcome"] is not None
                else math.inf,
                item["priority"],
                item["model"],
            )
        )
        selected = eligible[0] if eligible else None
        selection_basis = "only-eligible-route" if len(eligible) == 1 else "least-cost-per-accepted-outcome"
    status = "route-selected" if selected else ("no-cost-comparable-local-route" if blockers else "no-eligible-local-route")
    return {
        "format": "cd-local-route-plan/v1",
        "policy_id": policy.get("id"),
        "request_id": request.get("id"),
        "request_sha256": request_hash(request),
        "inventory_observed_at": inventory_value.get("observed_at"),
        "status": status,
        "selected": selected,
        "selection_basis": selection_basis,
        "decision_blockers": blockers,
        "candidates": candidates,
        "boundary": "Selection is limited to installed, explicitly qualified local candidates. It grants no execution authority.",
    }


def execute(plan_value: dict[str, Any], request: dict[str, Any], execute_flag: bool, timeout: float) -> dict[str, Any]:
    selected = plan_value.get("selected")
    if not selected or plan_value.get("status") != "route-selected":
        raise RouteError("no eligible local route is selected")
    if not execute_flag or request.get("execution_authorized") is not True:
        raise RouteError("local execution requires both --execute and execution_authorized: true in the request")
    if (request.get("required") or {}).get("tool_use"):
        raise RouteError("tool use is outside the v0.2 local executor")
    endpoint = local_endpoint(selected["endpoint"])
    payload: dict[str, Any] = {
        "model": selected["model"],
        "prompt": request["prompt"],
        "stream": False,
        "options": selected.get("options") or {},
    }
    if request.get("system"):
        payload["system"] = request["system"]
    if isinstance(selected.get("think"), bool):
        payload["think"] = selected["think"]
    value = request_json(endpoint, "/api/generate", payload, timeout)
    duration_ns = value.get("total_duration") if isinstance(value.get("total_duration"), int) else None
    prompt_tokens = value.get("prompt_eval_count") if isinstance(value.get("prompt_eval_count"), int) else 0
    output_tokens = value.get("eval_count") if isinstance(value.get("eval_count"), int) else 0
    record = {
        "format": "cd-local-cognition-result/v1",
        "request_id": request.get("id"),
        "request_sha256": request_hash(request),
        "model": selected["model"],
        "endpoint": endpoint,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "response": value.get("response"),
        "done": value.get("done"),
        "done_reason": value.get("done_reason"),
        "metrics": {
            "total_duration_ns": duration_ns,
            "load_duration_ns": value.get("load_duration"),
            "prompt_eval_count": prompt_tokens,
            "prompt_eval_duration_ns": value.get("prompt_eval_duration"),
            "eval_count": output_tokens,
            "eval_duration_ns": value.get("eval_duration"),
        },
        "workflow_run": {
            "format": "cd-cognition-workflow-run/v1",
            "id": request.get("id") or "local-run",
            "mode": "actual",
            "route_id": f"ollama:{selected['model']}",
            "attempts": 1,
            "accepted_outcomes": 0,
            "elapsed_hours": duration_ns / 3_600_000_000_000 if duration_ns else None,
            "eligible": True,
            "floor_failures": [],
            "quantities": {
                "input_tokens": prompt_tokens,
                "output_tokens": output_tokens,
                "requests": 1,
                "infrastructure_hours": duration_ns / 3_600_000_000_000 if duration_ns else 0,
            },
            "direct_costs": {},
            "assumptions": ["Outcome acceptance remains unrecorded until the user or evaluator applies the workload oracle."],
        },
        "boundary": "One local text generation only. No tools, cloud route, paid workload, account change, or automatic fallback executed.",
    }
    return record


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--endpoint", default="http://127.0.0.1:11434")
    inv.add_argument("--timeout", type=float, default=10.0)
    inv.add_argument("--output")
    for name in ("plan", "run"):
        command = sub.add_parser(name)
        command.add_argument("--policy", required=True)
        command.add_argument("--request", required=True)
        command.add_argument("--inventory")
        command.add_argument("--endpoint", default="http://127.0.0.1:11434")
        command.add_argument("--timeout", type=float, default=120.0)
        command.add_argument("--output")
        if name == "run":
            command.add_argument("--execute", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        if args.command == "inventory":
            emit(inventory(args.endpoint, args.timeout), args.output)
            return 0
        policy = load(args.policy)
        request = load(args.request)
        inventory_value = load(args.inventory) if args.inventory else inventory(args.endpoint, args.timeout)
        plan_value = plan(policy, request, inventory_value)
        if args.command == "plan":
            emit(plan_value, args.output)
        else:
            emit(execute(plan_value, request, args.execute, args.timeout), args.output)
        return 0
    except RouteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
