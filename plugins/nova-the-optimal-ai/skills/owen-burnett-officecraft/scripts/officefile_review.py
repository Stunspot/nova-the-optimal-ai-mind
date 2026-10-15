"""Review consistency for an exact artifact, production basis and intended use.

Structured records do not authenticate a reviewer, approver, evidence or facts.
"""
from datetime import datetime, timedelta, timezone
from officefile_relationships import basis_digest


def text(value):
    return isinstance(value, str) and bool(value.strip())


def timestamp(value):
    if not text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None and parsed <= datetime.now(timezone.utc) + timedelta(minutes=5)
    except ValueError:
        return False


def conditions_closed(entry, artifact_id, intended_use, approval_owner):
    conditions = entry.get('conditions')
    if not isinstance(conditions, list):
        return False
    for condition in conditions:
        if not isinstance(condition, dict):
            return False
        if not isinstance(condition.get('artifact_ids'), list):
            return False
        if artifact_id not in condition['artifact_ids'] or condition.get('intended_use') != intended_use:
            continue
        if condition.get('status') == 'met' and text(condition.get('resolution_evidence')):
            continue
        acceptance = condition.get('acceptance')
        if condition.get('status') == 'residual_accepted' and isinstance(acceptance, dict) and acceptance.get('owner') == approval_owner and acceptance.get('approved_use') == intended_use and acceptance.get('authority_kind') in ('user', 'accountable_owner') and timestamp(acceptance.get('accepted_at')) and text(acceptance.get('rationale')):
            continue
        return False
    return True


def matches(entry, artifact_id, digest, artifact):
    records = entry.get('reviewed_artifacts')
    return isinstance(records, list) and any(isinstance(item, dict) and item.get('artifact_id') == artifact_id and item.get('sha256') == digest and item.get('input_basis_sha256') == basis_digest(artifact) for item in records)


def current_entries(review, state, artifact_id, digest, artifact, use=None):
    """Select declarations for these exact bytes/basis/state, scoped by use."""
    entries = []
    for field in ('operator_review', 'independent_review'):
        entry = review.get(field, {})
        if not isinstance(entry, dict) or entry.get('status') not in ('PASS', 'PASS_WITH_CONDITIONS', 'REVISE', 'BLOCKED'):
            continue
        if entry.get('officefile_state') != state or not text(entry.get('intended_use')):
            continue
        if use is not None and entry['intended_use'] != use:
            continue
        if matches(entry, artifact_id, digest, artifact):
            entries.append(entry)
    return entries


def review_supported(review, state, artifact_id, digest, artifact):
    entries = current_entries(review, state, artifact_id, digest, artifact)
    # A reviewed artifact can have a useful conditional review for one use.
    # A conflicting current verdict defeats that use, not every unrelated use.
    for use in {entry['intended_use'] for entry in entries}:
        scoped = [entry for entry in entries if entry['intended_use'] == use]
        if all(entry['status'] in ('PASS', 'PASS_WITH_CONDITIONS') for entry in scoped):
            return True
    return False


def use_supported(review, state, artifact_id, digest, artifact, use, owner):
    entries = current_entries(review, state, artifact_id, digest, artifact, use)
    # Current reviews compose as constraints, not competing approval grants.
    return bool(entries) and all(
        entry['status'] in ('PASS', 'PASS_WITH_CONDITIONS')
        and conditions_closed(entry, artifact_id, use, owner)
        for entry in entries
    )


def validate_review_bindings(review, artifacts, errors):
    for field in ('operator_review', 'independent_review'):
        entry = review.get(field)
        if not isinstance(entry, dict) or entry.get('status') not in ('PASS', 'PASS_WITH_CONDITIONS'):
            continue
        label = 'review/' + field
        if entry.get('record_version') != 'officecraft-review-entry/v2':
            errors.append(label + ': legacy or missing review binding; retain as history and perform a current scoped review')
        if not text(entry.get('intended_use')) or not text(entry.get('reviewer_role')) or not timestamp(entry.get('reviewed_at')):
            errors.append(label + ': intended_use, reviewer_role and observed reviewed_at are required')
        reviewed = entry.get('reviewed_artifacts')
        if not isinstance(reviewed, list):
            continue
        ids = [x.get('artifact_id') for x in reviewed if isinstance(x, dict)]
        for binding in reviewed:
            if not isinstance(binding, dict):
                continue
            artifact = artifacts.get(binding.get('artifact_id')) if isinstance(binding.get('artifact_id'), str) else None
            if artifact is not None and binding.get('input_basis_sha256') != basis_digest(artifact):
                errors.append(label + ': reviewed production basis differs from current artifact basis')
        conditions = entry.get('conditions')
        if not isinstance(conditions, list):
            errors.append(label + ': conditions must be a structured array, including empty when none')
            continue
        if entry.get('status') == 'PASS_WITH_CONDITIONS' and not conditions:
            errors.append(label + ': conditional PASS needs at least one structured condition')
        condition_ids = set()
        for condition in conditions:
            if not isinstance(condition, dict):
                errors.append(label + ': each condition must be an object'); continue
            cid = condition.get('id')
            if not text(cid) or cid in condition_ids:
                errors.append(label + ': condition IDs must be unique nonempty strings')
            else:
                condition_ids.add(cid)
            affected = condition.get('artifact_ids')
            if not isinstance(affected, list) or not affected or any(not isinstance(x, str) or x not in ids for x in affected):
                errors.append(label + ': condition must name reviewed artifacts')
            if not text(condition.get('statement')) or condition.get('intended_use') != entry.get('intended_use'):
                errors.append(label + ': condition needs its statement and exact intended use')
            status = condition.get('status')
            if status not in ('open', 'met', 'residual_accepted'):
                errors.append(label + ': condition status must be open, met or residual_accepted')
            if status == 'met' and not text(condition.get('resolution_evidence')):
                errors.append(label + ': met condition needs actual resolution evidence')
            if status == 'residual_accepted':
                acceptance = condition.get('acceptance')
                if not isinstance(acceptance, dict) or not text(acceptance.get('owner')) or acceptance.get('authority_kind') not in ('user', 'accountable_owner') or acceptance.get('approved_use') != entry.get('intended_use') or not timestamp(acceptance.get('accepted_at')) or not text(acceptance.get('rationale')):
                    errors.append(label + ': residual acceptance needs scoped attributable owner authority and rationale')
            if entry.get('status') == 'PASS' and status != 'met':
                errors.append(label + ': unconditional PASS cannot contain an open or accepted-residual condition')
        findings = entry.get('material_findings', [])
        if not isinstance(findings, list):
            errors.append(label + ': material_findings must be an array'); continue
        for finding in findings:
            if not isinstance(finding, dict):
                errors.append(label + ': material finding must be an object'); continue
            if finding.get('status') != 'open':
                continue
            if finding.get('required_disposition') in ('REVISE', 'BLOCKED') or entry.get('status') == 'PASS':
                errors.append(label + ': open material finding contradicts passing disposition')
            elif not isinstance(finding.get('condition_id'), str) or finding.get('condition_id') not in condition_ids:
                errors.append(label + ': open conditional finding needs a linked structured condition')