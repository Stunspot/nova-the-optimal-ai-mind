# Preserve and migrate a v1 ledger

Older v1 files remain readable in the desk and validator. Their approval fields have no v2 content binding. Keep the original file unchanged. The bundled v1 example is historical and is not a ready-to-adopt current proposal.

From the skill folder, with an existing empty output directory, run `python -B scripts/answerlayer.py migrate OLD.json NEW.json`. Expect `migrated_to_new_file`. Unknown extension fields survive; `migration.source_sha256` binds the exact original bytes, and old approval/patch assertions are retained under migration metadata. Current approvals start empty. Missing source inspections, dates and support remain unknown.

Run `python -B scripts/answerlayer.py validate NEW.json`. Then inspect the migrated answer, scope and dates against the original. Prior baseline history is not invented. Repair a new checkpoint if the source is malformed; the error identifies what needs attention. A mismatch between a legacy patch's before text and the baseline is retained as an ineligible proposal, never guessed away.

Before adopting any migrated proposal, inspect real evidence, record known current/result cutoffs, map source support, verify the exact before span and record actual content-bound authority. The [reference](../../knowledge/native-ledger-reference.md) describes those fields. Migration alone is neither review nor approval.
