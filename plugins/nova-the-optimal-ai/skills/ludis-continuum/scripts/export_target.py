from __future__ import annotations

import argparse
import base64
import html
import json
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from adapters import (
    ALCHEMY_ADAPTER_ID,
    FOUNDRY_ADAPTER_ID,
    AdapterError,
    render_alchemy_character_json,
    render_foundry_v14_bundle,
    validate_alchemy_character_files,
    validate_foundry_v14_bundle,
)
from exportlib import (
    ExportError,
    exclusive_output_locks,
    capture_campaign,
    freeze_file,
    pretty_json_bytes,
    project_ledger,
    publish_file_if_absent,
    recheck_frozen_files,
    sha256_bytes,
    sha256_file,
    validate_archive_member_names,
    write_deterministic_zip,
)


TARGETS = {"alchemy", "foundry-v14"}
_IMAGE_MEDIA = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
_TEXT_SUFFIXES = {".json", ".md", ".txt", ".csv", ".mjs", ".js"}


class TargetExportError(ValueError):
    """A target bundle could not be built or verified safely."""


@dataclass(frozen=True)
class TargetBuildResult:
    artifact: Path
    artifact_sha256: str
    audit: Path
    preview: Path
    target: str
    audience: str
    finalized: bool


def _safe_members(files: Mapping[str, bytes]) -> None:
    for name, data in files.items():
        if not isinstance(name, str) or not isinstance(data, bytes):
            raise TargetExportError("target adapter files must map string paths to bytes")
    try:
        validate_archive_member_names(files)
    except ExportError as exc:
        raise TargetExportError(f"unsafe target bundle member: {exc}") from exc


def _decode_report(files: Mapping[str, bytes]) -> dict[str, Any]:
    data = files.get("reports/loss-report.json")
    if not isinstance(data, bytes):
        raise TargetExportError("target loss report is missing")
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TargetExportError(f"target loss report is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise TargetExportError("target loss report must be a JSON object")
    return value


def _adapter_for(target: str):
    if target == "alchemy":
        return ALCHEMY_ADAPTER_ID, validate_alchemy_character_files
    if target == "foundry-v14":
        return FOUNDRY_ADAPTER_ID, validate_foundry_v14_bundle
    raise TargetExportError(f"unsupported target: {target}")


def render_target(
    target: str,
    projection: Mapping[str, Any],
    assets: Mapping[str, Path],
    *,
    module_id: str | None = None,
    module_title: str | None = None,
) -> dict[str, bytes]:
    if target == "alchemy":
        files = render_alchemy_character_json(projection, assets)
    elif target == "foundry-v14":
        files = render_foundry_v14_bundle(
            projection,
            assets,
            module_id=module_id,
            module_title=module_title,
        )
    else:
        raise TargetExportError(f"unsupported target: {target}")
    _safe_members(files)
    report = _decode_report(files)
    if report.get("status") == "blocked":
        reasons = [
            str(item.get("message"))
            for item in report.get("items", [])
            if isinstance(item, dict) and item.get("severity") == "blocked"
        ]
        raise TargetExportError("target mapping is blocked: " + ("; ".join(reasons) or "no target records were emitted"))
    _, validator = _adapter_for(target)
    errors = validator(files)
    if errors:
        raise TargetExportError("target adapter output failed validation: " + "; ".join(errors))
    return files


def _preview_html(
    files: Mapping[str, bytes],
    target: str,
    audience: str,
    projection: Mapping[str, Any],
) -> bytes:
    campaign = projection.get("campaign", {})
    title = campaign.get("title") if isinstance(campaign, Mapping) else None
    title = str(title or "Untitled campaign")
    alt_by_id = {
        str(asset.get("id")): str(asset.get("alt_text"))
        for asset in projection.get("assets", [])
        if isinstance(asset, Mapping)
        and isinstance(asset.get("id"), str)
        and isinstance(asset.get("alt_text"), str)
        and asset.get("alt_text", "").strip()
    }
    alt_by_path: dict[str, str] = {}
    if target == "foundry-v14" and "data/ludis-foundry-v14.json" in files:
        try:
            payload = json.loads(files["data/ludis-foundry-v14.json"].decode("utf-8"))
            for item in payload.get("assets", []):
                if not isinstance(item, Mapping) or not isinstance(item.get("path"), str):
                    continue
                source_id = item.get("sourceId")
                authored = item.get("altText")
                if isinstance(authored, str) and authored.strip():
                    alt_by_path[item["path"]] = authored
                elif isinstance(source_id, str) and source_id in alt_by_id:
                    alt_by_path[item["path"]] = alt_by_id[source_id]
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass

    rows = []
    details = []
    rendered_names: set[str] = set()
    for name, data in sorted(files.items()):
        digest = sha256_bytes(data)
        rows.append(
            "<tr><td>{}</td><td>{}</td><td><code>{}</code></td></tr>".format(
                html.escape(name), len(data), digest
            )
        )
        suffix = PurePosixPath(name).suffix.casefold()
        if suffix in _IMAGE_MEDIA:
            encoded = base64.b64encode(data).decode("ascii")
            alt_text = alt_by_path.get(name, "Preview of exported image asset {}".format(name))
            details.append(
                '<section><h2>{}</h2><img src="data:{};base64,{}" alt="{}"></section>'.format(
                    html.escape(name), _IMAGE_MEDIA[suffix], encoded, html.escape(alt_text, quote=True)
                )
            )
            rendered_names.add(name)
        elif suffix in _TEXT_SUFFIXES:
            try:
                rendered = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            details.append(
                "<section><h2>{}</h2><pre>{}</pre></section>".format(
                    html.escape(name), html.escape(rendered)
                )
            )
            rendered_names.add(name)
    non_rendered = [name for name in sorted(files) if name not in rendered_names]
    non_rendered_items = "".join("<li><code>{}</code></li>".format(html.escape(name)) for name in non_rendered)
    if not non_rendered_items:
        non_rendered_items = "<li>None; every current member is rendered below.</li>"
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ludis target-bundle preview</title>
<style>body{{font:16px/1.5 system-ui;max-width:80rem;margin:auto;padding:2rem}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #777;padding:.4rem;text-align:left;vertical-align:top}}code{{overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#eee;color:#111;padding:1rem}}img{{max-width:100%;height:auto;border:2px solid #555}}section{{margin-block:2rem}}</style></head>
<body><main><h1>{}: {} {} bundle preview</h1>
<p>This preview is one required review surface, not the whole candidate. Before approval, extract the candidate into a new directory, compare every member in this inventory with the candidate and audit, inspect or listen to every member not rendered here, and treat bundled code as text without executing it. Static validation does not prove live import or semantic spoiler safety.</p>
<table><thead><tr><th scope="col">Member</th><th scope="col">Bytes</th><th scope="col">SHA-256</th></tr></thead><tbody>{}</tbody></table><section><h2>Members not rendered here</h2><ul>{}</ul></section>{}</main></body></html>
""".format(
        html.escape(title), html.escape(audience), html.escape(target), "".join(rows), non_rendered_items, "".join(details)
    )
    return document.encode("utf-8")
def _sidecar(path: Path, label: str) -> Path:
    return path.with_name(path.name + f".{label}.json")


def _preview_path(path: Path) -> Path:
    return path.with_name(path.name + ".preview.html")


def build_target(
    campaign_root: Path,
    output: Path,
    target: str,
    audience: str,
    object_ids: Iterable[str] | None = None,
    *,
    module_id: str | None = None,
    module_title: str | None = None,
) -> TargetBuildResult:
    reserved_output = output.resolve()
    reserved_preview = _preview_path(reserved_output)
    reserved_audit = _sidecar(reserved_output, "audit")
    with exclusive_output_locks((reserved_output, reserved_preview, reserved_audit)):
        return _build_target_reserved(
            campaign_root,
            reserved_output,
            target,
            audience,
            object_ids,
            module_id=module_id,
            module_title=module_title,
        )


def _build_target_reserved(
    campaign_root: Path,
    output: Path,
    target: str,
    audience: str,
    object_ids: Iterable[str] | None = None,
    *,
    module_id: str | None = None,
    module_title: str | None = None,
) -> TargetBuildResult:
    if target not in TARGETS:
        raise TargetExportError(f"unsupported target: {target}")
    if audience not in {"gm", "player"}:
        raise TargetExportError("audience must be gm or player")
    if audience == "player" and not output.name.endswith(".candidate.zip"):
        raise TargetExportError("player output must end in .candidate.zip; approve it separately after review")
    if audience == "gm" and output.name.endswith(".candidate.zip"):
        raise TargetExportError("GM target output should be a final .zip")
    output = output.resolve()
    preview = _preview_path(output)
    audit = _sidecar(output, "audit")
    occupied = [path for path in (output, preview, audit) if path.exists()]
    if occupied:
        raise TargetExportError("immutable target path already exists: " + ", ".join(str(path) for path in occupied))
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".ludis-target-", dir=str(output.parent)) as temporary_name:
        temporary = Path(temporary_name)
        captured = capture_campaign(campaign_root, temporary / "capture")
        projection = project_ledger(captured.ledger, audience, object_ids)
        files = render_target(
            target,
            projection,
            captured.assets,
            module_id=module_id,
            module_title=module_title,
        )
        staged_artifact = temporary / output.name
        artifact_digest = write_deterministic_zip(staged_artifact, files)
        verification = verify_target_zip(staged_artifact)
        verification["path"] = output.name
        preview_bytes = _preview_html(files, target, audience, projection)
        staged_preview = temporary / preview.name
        staged_preview.write_bytes(preview_bytes)
        report = _decode_report(files)
        audit_data = {
            "format": "cd-ludis-target-audit/v1",
            "state": "approval_required" if audience == "player" else "finalized",
            "audience": audience,
            "target": target,
            "adapter": report.get("adapter"),
            "compatibility": report.get("compatibility"),
            "candidate_sha256" if audience == "player" else "artifact_sha256": artifact_digest,
            "preview_sha256": sha256_bytes(preview_bytes),
            "source_capture_digest": captured.source_digest,
            "object_ids": [obj["id"] for obj in projection["objects"]],
            "asset_ids": [asset["id"] for asset in projection["assets"]],
            "target_verification": verification,
            "loss_summary": report.get("summary"),
            "human_checks_required": ["semantic_spoilers", "rights_and_credits", "complete_member_inspection", "non_rendered_media_review", "code_review_as_text_without_execution", "live_target_import", "visual_rendering"],
        }
        staged_audit = temporary / audit.name
        staged_audit.write_bytes(pretty_json_bytes(audit_data))
        try:
            publish_file_if_absent(staged_preview, preview, "target preview")
            publish_file_if_absent(staged_audit, audit, "target audit")
            publish_file_if_absent(staged_artifact, output, "target artifact")
        except ExportError as exc:
            raise TargetExportError(str(exc)) from exc
    return TargetBuildResult(output, artifact_digest, audit, preview, target, audience, audience == "gm")


def _zip_files(path: Path) -> dict[str, bytes]:
    if not path.is_file():
        raise TargetExportError(f"target bundle does not exist: {path}")
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        try:
            validate_archive_member_names(names)
        except ExportError as exc:
            raise TargetExportError(f"unsafe target bundle member: {exc}") from exc
        if archive.testzip() is not None:
            raise TargetExportError("target bundle has a CRC failure")
        files = {name: archive.read(name) for name in names}
    _safe_members(files)
    return files


def verify_target_zip(path: Path) -> dict[str, Any]:
    files = _zip_files(path)
    if "data/ludis-foundry-v14.json" in files or "module.json" in files:
        target = "foundry-v14"
    elif "_all.json" in files:
        target = "alchemy"
    else:
        raise TargetExportError("target bundle type is not recognized")
    adapter, validator = _adapter_for(target)
    errors = validator(files)
    if errors:
        raise TargetExportError("target bundle failed static validation: " + "; ".join(errors))
    report = _decode_report(files)
    if report.get("adapter") != adapter:
        raise TargetExportError("target loss report adapter does not match bundle contents")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "target": target,
        "adapter": adapter,
        "members": len(files),
        "compatibility": report.get("compatibility"),
        "loss_summary": report.get("summary"),
    }


def approve_target(candidate: Path, asserted_by: str, final: Path | None = None) -> tuple[Path, Path]:
    resolved_candidate = candidate.resolve()
    audit = _sidecar(resolved_candidate, "audit")
    preview = _preview_path(resolved_candidate)
    if final is None and resolved_candidate.name.endswith(".candidate.zip"):
        reserved_final = resolved_candidate.with_name(resolved_candidate.name[: -len(".candidate.zip")] + ".zip")
    elif final is not None:
        reserved_final = final.resolve()
    else:
        reserved_final = resolved_candidate.with_name(resolved_candidate.name + ".final")
    reserved_receipt = reserved_final.with_name(reserved_final.name + ".approval.json")
    with exclusive_output_locks((resolved_candidate, audit, preview, reserved_final, reserved_receipt)):
        return _approve_target_reserved(resolved_candidate, asserted_by, reserved_final if final is not None else None)


def _approve_target_reserved(candidate: Path, asserted_by: str, final: Path | None = None) -> tuple[Path, Path]:
    if not asserted_by.strip():
        raise TargetExportError("asserted_by is required")
    candidate = candidate.resolve()
    if not candidate.name.endswith(".candidate.zip"):
        raise TargetExportError("approval input must end in .candidate.zip")
    audit_path = _sidecar(candidate, "audit")
    preview_path = _preview_path(candidate)
    if not audit_path.is_file() or not preview_path.is_file():
        raise TargetExportError("candidate audit and preview sidecars are required")
    try:
        frozen_candidate = freeze_file(candidate, "candidate")
        frozen_preview = freeze_file(preview_path, "preview")
        frozen_audit = freeze_file(audit_path, "audit")
    except ExportError as exc:
        raise TargetExportError(str(exc)) from exc
    frozen_inputs = (frozen_candidate, frozen_preview, frozen_audit)
    try:
        audit = json.loads(frozen_audit.data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TargetExportError(f"candidate audit is invalid: {exc}") from exc
    candidate_digest = frozen_candidate.sha256
    preview_digest = frozen_preview.sha256
    if audit.get("format") != "cd-ludis-target-audit/v1" or audit.get("state") != "approval_required" or audit.get("audience") != "player":
        raise TargetExportError("audit does not describe an approval-ready player target candidate")
    if audit.get("candidate_sha256") != candidate_digest:
        raise TargetExportError("candidate bytes changed after audit; rebuild and review again")
    if audit.get("preview_sha256") != preview_digest:
        raise TargetExportError("preview bytes changed after audit; rebuild and review again")

    if final is None:
        final = candidate.with_name(candidate.name[: -len(".candidate.zip")] + ".zip")
    final = final.resolve()
    receipt = final.with_name(final.name + ".approval.json")
    if final in {candidate, preview_path, audit_path} or receipt in {candidate, preview_path, audit_path}:
        raise TargetExportError("final and approval receipt paths must not overlap candidate evidence")
    final.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".ludis-target-finalize-", dir=str(final.parent)) as temporary_name:
        temporary = Path(temporary_name)
        staged_input = temporary / "frozen-player-target.candidate.zip"
        staged_input.write_bytes(frozen_candidate.data)
        verified = verify_target_zip(staged_input)
        if verified.get("target") != audit.get("target"):
            raise TargetExportError("candidate target does not match its audit")
        try:
            recheck_frozen_files(frozen_inputs)
        except ExportError as exc:
            raise TargetExportError(str(exc)) from exc

        limitations = "Ludis binds this local assertion to exact frozen candidate, preview, and audit bytes; it does not authenticate identity or prove live target import."
        if final.exists() or receipt.exists():
            if not (final.is_file() and receipt.is_file()):
                raise TargetExportError("partial prior finalization exists; preserve it and choose a new --final path")
            try:
                frozen_final = freeze_file(final, "prior target final artifact")
                frozen_receipt = freeze_file(receipt, "prior target approval receipt")
            except ExportError as exc:
                raise TargetExportError(str(exc)) from exc
            try:
                previous = json.loads(frozen_receipt.data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise TargetExportError("prior target approval receipt is unreadable; preserve it and choose a new --final path") from exc
            expected_keys = {
                "format", "state", "target", "adapter", "artifact", "artifact_sha256",
                "candidate", "candidate_sha256", "preview", "preview_sha256", "audit",
                "audit_sha256", "asserted_by", "assertion_type", "approved_at", "limitations",
            }
            approved_at = previous.get("approved_at")
            valid_timestamp = False
            if isinstance(approved_at, str) and approved_at.endswith("Z"):
                try:
                    datetime.fromisoformat(approved_at[:-1] + "+00:00")
                    valid_timestamp = True
                except ValueError:
                    pass
            same_evidence = (
                frozen_final.sha256 == candidate_digest
                and frozen_receipt.data == pretty_json_bytes(previous)
                and set(previous) == expected_keys
                and previous.get("format") == "cd-ludis-local-approval/v1"
                and previous.get("state") == "finalized"
                and previous.get("target") == verified["target"]
                and previous.get("adapter") == verified["adapter"]
                and previous.get("artifact") == final.name
                and previous.get("artifact_sha256") == candidate_digest
                and previous.get("candidate") == candidate.name
                and previous.get("candidate_sha256") == candidate_digest
                and previous.get("preview") == preview_path.name
                and previous.get("preview_sha256") == preview_digest
                and previous.get("audit") == audit_path.name
                and previous.get("audit_sha256") == frozen_audit.sha256
                and previous.get("assertion_type") == "unauthenticated_local_operator_attestation"
                and valid_timestamp
                and previous.get("limitations") == limitations
            )
            if not same_evidence:
                raise TargetExportError(f"final path already contains different evidence: {final}")
            if previous.get("asserted_by") != asserted_by:
                raise TargetExportError("candidate was already finalized under a different local operator assertion")
            try:
                recheck_frozen_files((frozen_final, frozen_receipt))
            except ExportError as exc:
                raise TargetExportError(str(exc)) from exc
            return final, receipt

        asserted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        receipt_data = {
            "format": "cd-ludis-local-approval/v1",
            "state": "finalized",
            "target": verified["target"],
            "adapter": verified["adapter"],
            "artifact": final.name,
            "artifact_sha256": candidate_digest,
            "candidate": candidate.name,
            "candidate_sha256": candidate_digest,
            "preview": preview_path.name,
            "preview_sha256": preview_digest,
            "audit": audit_path.name,
            "audit_sha256": frozen_audit.sha256,
            "asserted_by": asserted_by,
            "assertion_type": "unauthenticated_local_operator_attestation",
            "approved_at": asserted_at,
            "limitations": limitations,
        }
        staged_final = temporary / final.name
        staged_receipt = temporary / receipt.name
        staged_final.write_bytes(frozen_candidate.data)
        if sha256_file(staged_final) != candidate_digest:
            raise TargetExportError("final copy failed digest verification")
        staged_receipt.write_bytes(pretty_json_bytes(receipt_data))
        try:
            recheck_frozen_files(frozen_inputs)
        except ExportError as exc:
            raise TargetExportError(str(exc)) from exc
        try:
            publish_file_if_absent(staged_receipt, receipt, "target approval receipt")
            publish_file_if_absent(staged_final, final, "approved target artifact")
        except ExportError as exc:
            raise TargetExportError(str(exc)) from exc
    if sha256_file(final) != candidate_digest:
        raise TargetExportError("final target artifact does not equal the approved candidate")
    return final, receipt
def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Build and verify offline Ludis target bundles.")
    sub = command.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Build an Alchemy or Foundry target ZIP.")
    build.add_argument("campaign", type=Path)
    build.add_argument("output", type=Path)
    build.add_argument("--target", choices=sorted(TARGETS), required=True)
    build.add_argument("--audience", choices=("gm", "player"), required=True)
    build.add_argument("--object", dest="objects", action="append", default=[])
    build.add_argument("--module-id", help="Foundry module id override.")
    build.add_argument("--module-title", help="Foundry module title override.")

    verify = sub.add_parser("verify", help="Run target-specific static validation against a ZIP.")
    verify.add_argument("bundle", type=Path)

    approve = sub.add_parser("approve", help="Approve exact player target candidate and preview bytes.")
    approve.add_argument("candidate", type=Path)
    approve.add_argument("--asserted-by", required=True)
    approve.add_argument("--final", type=Path)
    return command


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "build":
            if args.target != "foundry-v14" and (args.module_id or args.module_title):
                raise TargetExportError("--module-id and --module-title apply only to foundry-v14")
            result = build_target(
                args.campaign,
                args.output,
                args.target,
                args.audience,
                args.objects or None,
                module_id=args.module_id,
                module_title=args.module_title,
            )
            state = "FINAL" if result.finalized else "APPROVAL REQUIRED"
            print(f"PASS: {state}: {result.artifact}")
            print(f"TARGET: {result.target}")
            print(f"SHA256: {result.artifact_sha256.upper()}")
            print(f"AUDIT: {result.audit}")
            print(f"PREVIEW: {result.preview}")
            if result.audience == "player":
                print("REVIEW: extract a new review copy; compare every member with the preview and audit; inspect or listen to non-rendered members; treat code as text and do not execute it before approval.")
            print("COMPATIBILITY: statically validated; live import unverified")
            return 0
        if args.command == "verify":
            report = verify_target_zip(args.bundle)
            print(f"PASS: {report['target']} target bundle; {report['members']} members")
            print(f"SHA256: {report['sha256'].upper()}")
            print("COMPATIBILITY: statically validated; live import unverified")
            return 0
        final, receipt = approve_target(args.candidate, args.asserted_by, args.final)
        report = verify_target_zip(final)
        print(f"PASS: FINALIZED UNCHANGED: {final}")
        print(f"TARGET: {report['target']}")
        print(f"SHA256: {report['sha256'].upper()}")
        print(f"APPROVAL: {receipt}")
        return 0
    except (AdapterError, ExportError, TargetExportError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
