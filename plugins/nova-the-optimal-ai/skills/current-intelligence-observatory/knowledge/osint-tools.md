# OSINT tool collection

Follow the case question to the next useful source. When public account, domain, certificate/registry or indexed service evidence could distinguish a live hypothesis, inspect the host workbench with `python scripts/osint_bridge.py discover`, then choose the smallest relevant query. If the workbench is absent and the user wants it installed, follow [OSINT setup](osint-setup.md) and use the bundled `scripts/setup_osint.py` in a customer-selected home. Ordinary public-source investigation remains usable during setup or when execution is unavailable.

The bridge resolves `--workbench`, `NOVA_OSINT_HOME`, then `NOVA_DATA_ROOT/integrations/osint`. On this Windows estate it also recognizes `E:\Indranet\Nova\integrations\osint`. Read that workbench's current `registry.json` and guide for installation state and provider limits. Installation and runtime success establish capability; a case's supplied authority and scope govern actual collection.

| Investigative need | Workbench command | Decision cue |
| --- | --- | --- |
| Candidate account locations | `username HANDLE --sites GitHub,GitLab` | Maigret; choose relevant sites. Extraction and recursion remain explicit. A shared handle is a candidate link. |
| Passive domain discovery | `domain YOUR_DOMAIN --sources crtsh,certspotter` | theHarvester; named P0 providers and bounded results. |
| Chained certificate/registry enrichment | `spiderfoot YOUR_DOMAIN --max-requests 20 --deadline 120` | Reviewed SpiderFoot domain profile; contact extraction and provenance graph. |
| Existing indexed network-service data | `shodan host IP`, `shodan count QUERY`, or `shodan search QUERY --limit 10` | Environment-supplied API key and entitlement; query existing records. |
| Offline workflow demonstration | `spiderfoot-demo` | Built-in synthetic provider fixtures; no external requests. |

Pass these commands through `python scripts/osint_bridge.py run ...`. Use `--dry-run` with a real query to inspect its concrete scope. The workbench preserves its own time-stamped run reports and exit status. Missing credentials, failed providers and partial results are evidence gaps to report; choose a different useful source within the existing scope when one is available. Blackbird has no enabled runtime. Sherlock remains a source comparison baseline.

Preserve a completed or partial run with:

```powershell
python scripts/osint_bridge.py attach-run --case CASE.json --run RUN_DIRECTORY --output CASE-with-osint.json
python scripts/observatory_guardrail.py validate-case CASE-with-osint.json
```

Frame the native case first and choose a new case filename beside it, keeping existing relative evidence paths valid. Attachment copies report files beside the new case, hashes each capture, records the native exit state and preserves the original case. Local file capture URIs identify actual derived tool reports; they do not imply that a provider page was captured or authenticated. Review captures and original provider evidence before making claims. Tool events remain `tool-reported`, with unrated confidence and explicit uncertainty. The bridge adds no identities, ownership relations, accepted claims or assessments; a new attachment puts an already ready case back into provisional review. Keep provider dependence, synthetic fixtures, incomplete scans and observation time distinct from event time. Graph edges and correlations nominate leads for source inspection.

For a synthetic investigation, frame a case about what `example.test` fixtures report, run `spiderfoot-demo`, attach its emitted run directory, validate the case and generate projections with the native guardrail. Report the fixture result and remaining live-provider gap. Follow a real investigation only when the user's actual scope calls for it.
