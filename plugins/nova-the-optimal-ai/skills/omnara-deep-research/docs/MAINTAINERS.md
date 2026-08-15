# Maintain and release Omnara

This guide is for people changing the standalone skill, campaign format, scripts, or public documentation.

## Preserve the product boundary

Omnara is a deep-research skill. Do not turn the README into a generic AI-research promise or claim a standalone plugin installation unless the repository actually ships and verifies that package.

Keep these distinctions stable:

- inquiry, corpus, claims, and report;
- discovered, inspected, opened, deeply read, excluded, duplicate, inaccessible, and cited states;
- structural citation integrity and semantic entailment;
- research work and external action authority;
- source-tree availability and host activation.

## Source authority

The operative entrypoint is [`../SKILL.md`](../SKILL.md). Its focused doctrine is under [`../references/`](../references/), the integrated persona is under [`../personas/`](../personas/), and the reusable state contract is split between [`../schemas/research-campaign.schema.json`](../schemas/research-campaign.schema.json), the campaign template, and `research_campaign.py`.

The retained canonical inquiry reference is [`../references/canonical/inquiry-engine-v1.md`](../references/canonical/inquiry-engine-v1.md). If it changes intentionally, update its SHA-256 in `scripts/validate_release.py` and record the provenance of the change.

Do not add expected hashes for canonical files that are not actually shipped.

## Change the campaign format deliberately

When changing states, phases, statuses, fields, or completion rules, update all affected surfaces together:

- `schemas/research-campaign.schema.json`;
- `assets/campaign-vault/campaign.json`;
- `scripts/research_campaign.py`;
- `scripts/citation_audit.py` when citation rules change;
- `docs/CAMPAIGN-VAULT.md`;
- `docs/WORKFLOW.md`;
- examples and fallback instructions;
- the format identifier when compatibility breaks.

Preserve old identifiers or provide a migration path. Do not silently reinterpret an existing field.

## Change a script with a recoverable test

At minimum, run:

```shell
python scripts/validate_release.py .
python scripts/research_campaign.py init /tmp/omnara-maintainer-test \
  --title "Maintainer test" \
  --query "Can the updated campaign initialize?" \
  --tier focused
python scripts/research_campaign.py validate /tmp/omnara-maintainer-test
python scripts/research_campaign.py summary /tmp/omnara-maintainer-test
```

Add ordered draft sections and run report assembly when `assemble_report.py` changes. Add a small, nonprivate evidence fixture and test both failing and passing citation-audit behavior when citation rules change.

Use a temporary directory appropriate to your operating system and remove it after inspection.

## Review documentation by user task

Before release, walk these paths:

1. A first-time user can understand the promise and activation boundary from the README.
2. The START HERE path produces a valid initial campaign without hidden prerequisites.
3. A researcher can distinguish all source states and repair validation failures.
4. A reviewer can determine exactly what each validation command proves.
5. A user blocked by missing search, PDF, file, paid, or authenticated access has a safe stopping state.
6. A maintainer can find source authority, change triggers, and rerun instructions.

Do not cosmetically rewrite runtime reference files as onboarding copy. Keep the human journey in `README.md`, `START-HERE.md`, and `docs/`; keep doctrine close to the skill.

## Release checklist

- Run `python scripts/validate_release.py .`.
- Run campaign initialization, validation, summary, and assembly smoke tests.
- Run a structural citation-audit fixture.
- Run the Hesperos Markdown linter and inspect every finding manually.
- Check local links.
- Review security, privacy, and access-boundary language.
- Confirm version and provenance statements.
- Record what was tested, environment, result, and what remains untested.
- Use an independent documentation/accessibility review for consequential releases.

A passing local validator is package evidence. It is not host-installation evidence, semantic research quality, accountable approval, or a formal accessibility assessment.
