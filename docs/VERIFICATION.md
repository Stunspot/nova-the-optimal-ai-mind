# Verification and evidence

Nova Free 3.1.1 separates source qualification from final archive construction.

## Source qualification

From the source repository, regenerate custody and run the local deterministic checks:

    python -B -X utf8 tools/generate_source_lock.py
    python -B -X utf8 -m unittest discover -s tests -v
    python -B -X utf8 tools/check_documentation.py
    python -B -X utf8 docs/check_site.py
    git diff --check

These checks cover one-plugin topology, exact twenty-seven-root source parity, seventeen nested MIND Cores, rights-bundle parity, reconciled component metadata, forbidden-runtime absence, state-custody boundaries, build determinism, documentation structure, local links, and adversarial verifier behavior.

A frozen source candidate then receives a full Hesperos documentation cycle and a TestForge operator campaign with independent review. Their records must identify the source checkpoint, environment, executed commands, evidence limits, and rerun conditions.

## Final build and package verification

After qualification evidence is accepted and committed, confirm that Git reports no tracked or untracked source drift, then run:

    python -B -X utf8 tools/build_release.py --repo . --require-clean
    python -B -X utf8 tools/verify_package.py dist/nova-the-optimal-ai-free-3.1.1

The builder creates the complete customer, Codex, and Claude-compatible archives plus twenty-seven standalone Claude folders and ZIPs. It raw-validates local and central filename bytes as strict UTF-8, requires the UTF-8 flag for non-ASCII names, compares exact staged inventory, and reads every member before accepting any archive. Each standalone artifact carries a nova-free-rights envelope; relevant TestForge, Agent Swarm, or career component notices travel inside it.

A package PASS establishes the exercised archive inventory, exact payload bytes, rights custody, per-file checksums, deterministic structure, host parity, source binding, and truthful not-published state. It does not establish fresh-host marketplace acceptance, installation, discovery, enabled state, restart behavior, model attention, routing quality, live tools, external-service behavior, publication, or customer outcomes.

No GitHub Actions run on a GitHub-hosted runner is claimed unless a specific authorized run and result are recorded. Local evidence neither impersonates nor requires hosted execution.
