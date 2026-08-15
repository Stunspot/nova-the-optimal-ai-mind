# Run your first Omnara research campaign

The goal is one useful, inspectable research result before you learn every ledger and status. Omnara should make the research path clearer, not make you operate a tiny bureaucracy for sport.

## 1. Confirm how Omnara is available

Use the path that matches your host.

### Omnara is installed through Nova

Begin a fresh task and explicitly invoke the skill:

```text
Use $omnara-deep-research.
```

Nova remains the front-facing collaborator. Omnara performs the backstage research work unless you explicitly ask to speak with Omnara.

### You have this standalone source tree

This checkout contains an individual skill, not a marketplace-ready plugin. Import or place the directory where your host discovers skills, using that host's current instructions. A successful import should expose the selector `omnara-deep-research` and the display name **OMNARA Deep Research**.

If the host cannot load skills but can accept a long prompt, use [`fallbacks/universal-copy-paste-workflow.md`](fallbacks/universal-copy-paste-workflow.md).

## 2. Give Omnara a decision-shaped inquiry

Use this template and replace the bracketed text:

```text
Use $omnara-deep-research.

Investigate: [the exact question].
Audience and decision use: [who will use the result and what they must decide].
Scope: [included topics, geography, population, product version, or jurisdiction].
Time horizon and evidence cutoff: [dates or freshness requirement].
Required evidence: [primary records, research, official documentation, field evidence, counterevidence].
Exclusions: [what not to investigate].
Deliverable: [brief, report, comparison, recommendation, length, citation style].
```

A narrow current fact may need one accountable source. A contested policy, scientific, historical, or systems question may earn a full campaign. Do not request a theatrical source quota unless the decision genuinely requires it.

## 3. Check the first response

Before deep retrieval begins, the response should make these things legible:

- the preserved inquiry;
- the audience and decision use;
- the scope, time horizon, and exclusions;
- the major coverage areas and competing explanations;
- the likely source ecosystems;
- the evidence burden and important access boundaries;
- the next useful research move.

Omnara may ask one clarifying question when the answer would materially change scope, consequence, access authority, architecture, or acceptance. It should not make you repeat information already supplied.

## 4. Create a durable campaign vault when needed

For work that must be resumed, audited, or handed off, initialize a vault from the repository root:

```shell
python scripts/research_campaign.py init campaigns/passkeys \
  --title "Passkey adoption decision" \
  --query "Should small organizations adopt passkeys for customer accounts in 2026?" \
  --tier focused
```

On Windows PowerShell, use the same command on one line or use the backtick as the line-continuation character. Substitute `python3` or `py -3` when that is your Python launcher.

Expected result:

```text
INITIALIZED: campaigns/passkeys
```

The command copies the campaign template, inserts the title and verbatim inquiry, records UTC timestamps, and creates the draft directory used by report assembly.

## 5. Validate before adding evidence

```shell
python scripts/research_campaign.py validate campaigns/passkeys
```

Expected result:

```text
VALID: campaigns/passkeys
```

This proves that the initial campaign structure and counters are internally consistent. It does not prove that research has been performed.

## 6. Work from the first unverified edge

During research, update the vault when evidence changes the campaign:

1. Record each search in `query-ledger.jsonl`.
2. Record every retained candidate in `source-ledger.jsonl` before counting it as inspected.
3. Write `notes/S###.md` before marking a source `deeply-read`.
4. Link claims to source IDs in `claim-ledger.jsonl`.
5. Update `coverage-matrix.md` and `contradictions.md` as the field changes.
6. Keep `campaign.json` counters synchronized with the ledgers.
7. Store ordered report sections in `draft/` with names such as `01-orientation.md` and `99-bibliography.md`.

The [campaign-vault reference](docs/CAMPAIGN-VAULT.md) gives the minimum validated fields and recommended evidence fields.

## 7. Assemble and audit the report

When the draft sections are ready:

```shell
python scripts/assemble_report.py campaigns/passkeys
python scripts/citation_audit.py campaigns/passkeys
```

The assembly command writes `report.md` and `report-metrics.json`. The citation command writes `citation-audit-structural.json`.

A passing structural audit means citation markers resolve to eligible, deeply read source records with substantive notes and claim links. It does not establish that those sources entail the report's wording.

## 8. Finish with an evidence boundary

A usable handoff includes:

- the report;
- scope and evidence cutoff;
- source-state counts;
- coverage disposition;
- important contradictions;
- structural citation result;
- semantic entailment disposition;
- limitations and inaccessible evidence;
- budget use;
- refresh triggers;
- the exact resume point when work is incomplete.

When a dependency disappears or a budget stops the campaign, preserve the useful work and name the assurance that was lost. Continue with [Troubleshooting and recovery](docs/TROUBLESHOOTING.md) rather than pretending the gap is completion.
