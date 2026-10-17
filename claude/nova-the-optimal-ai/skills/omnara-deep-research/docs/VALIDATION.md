# Check what the result actually claims

Run commands from the complete folder containing SKILL.md. Python 3.10+ and the standard library are sufficient. Use `python3` where appropriate.

## Exact package and source

`python -B scripts/validate_release.py . --profile source` checks current cargo, required room and research files, the preserved canonical inquiry hash, JSON syntax and static local Markdown/HTML paths. An extracted candidate also checks every PACKAGE-CONTENTS.json byte hash. `--profile runtime` checks the current runtime dependency set; the complete package is the recommended portable route. It does not prove installation or host invocation.

Maintainers run `python -B -m unittest discover -s tests -v` in the repository. Tests are development evidence and need not be shipped as customer runtime. Do not report a zero-test run in an extracted package as a passing product test.

## Create and validate

Choose a new directory outside the package:

```text
python scripts/research_campaign.py init <new-campaign> --title "A real question" --query "What evidence would change this answer?" --tier focused
python scripts/research_campaign.py validate <new-campaign>
python scripts/research_campaign.py summary <new-campaign>
```

A valid empty campaign establishes structure, not research. Validate checks types, joins, compatible source history, clocks/cutoff, counter consistency and completion declarations. A failed check names the affected record; [native files](CAMPAIGN-VAULT.md) explain the contract.

## Assemble, inspect and audit

`python scripts/assemble_report.py <campaign-folder>` joins immediate draft Markdown in lexical filename order. A separately changed report is preserved unless you deliberately use `--replace`; replacement saves its prior bytes under `.assembly-history`. Page counts are layout-dependent estimates, not rendered pages.

`python scripts/citation_audit.py <campaign-folder>` checks visible body markers, source eligibility, note/claim links and a visible bibliography containing exact source titles and locators. HTML comments and fenced examples cannot supply required evidence. The projection is bounded Markdown handling, not arbitrary HTML renderer conformance. A no-source result receives an explicit warning and still needs real semantic review of the absence boundary.

`python scripts/research_campaign.py review-subject <campaign-folder>` prints the actual review subject without writing anything. Follow [the review contract](../references/review-contract.md) to inspect the report and sources and record a review. Then set both phase and status to complete and validate again. Recomputing a digest is not performing review. Reviewer fields and hashes cannot authenticate truth, identity or independence.

## Scope of evidence

The retained [worked inquiry](../examples/sea-level-comparison/report.md) is actual source-method research with author in-process review. Local tests challenge malformed input, stale claims/notes/scope, hidden bibliography, chronology, exclusion history, no-evidence outcomes, overwrite protection and room recovery. Current package evidence is described in [the documentation boundary](../verification/documentation-review.md). Independent model trials, participant studies, assistive-technology conformance, fresh-host activation and publication are separate claims.
