# Verification and evidence

Nova Free 4.3.2 separates source qualification from final archive construction. This guide is for maintainers with the source repository; the extracted customer package does not include a buildable checkout. Current source preparation is not a READY verdict or a delivered release.

## Qualify the actual source

Complete the candidate first: one plugin, 28 native roots, 17 nested Faculty Cores, current host metadata, current guides, explicit owner selection and matching root/plugin rights. Preserve the prior accepted source and user work. Check that `design/source-map.json` identifies the bytes actually selected and records edition adaptations without promoting historical commits into current source claims.

After promoting a reviewed candidate into its canonical source layout, regenerate its exact source lock and inspect the diff:

    python -B -X utf8 tools/generate_source_lock.py
    git diff --check

Run the focused repository checks whose results could change this deliverable, plus applicable documentation and local-link checks. Record what ran and its actual scope; a list of available checks is not evidence that they ran. Carry sound component, native and documentation evidence forward when the relevant bytes, inputs and conditions remain unchanged.

Use maintained TestForge for a frozen finished source candidate, with sparse consequential checks and independent review. Preserve each materially authored guide's Hesperos receipt and test the current reader journey. Do not reissue unchanged guides as newly authored. A product defect ends that readiness cycle and returns the candidate to builder custody; a repaired successor needs its own current cutoff. Do not create release archives, checksums or seals during an active readiness cycle before its verdict and review.

## Build and verify after acceptance

Once source qualification and independent review are accepted, commit the intended source and evidence checkpoint. Preserve unrelated user work in its existing checkout; use an isolated release checkout when needed. Confirm the release checkout has no tracked or untracked source drift, then run:

    python -B -X utf8 tools/build_release.py --repo . --require-clean
    python -B -X utf8 tools/verify_package.py dist/nova-the-optimal-ai-free-4.3.2

The builder requires matching product, plugin, loadout and source-lock versions. It supports the retained 3.8.1 and 4.0.0 baselines and current 4.3.2 identity. Its explicit `--plugin-source` option can select a prepared plugin with the corresponding source-root documents and lock; that option does not bypass source identity, rights or clean-checkpoint requirements.

The final builder creates the complete customer and host archives plus 28 standalone Claude folders and ZIPs. It validates local and central ZIP filename bytes, exact inventories and member bytes. Each standalone artifact preserves its nova-free-rights envelope and applicable component notices. Verify the complete extracted package and fresh extracted archive contents before delivery; failed inventories or mismatched bytes are delivery defects.

A package PASS does not establish fresh-host use. It supports only the exercised inventory, payload, rights, checksums, host parity and source binding. Installation, discovery, enabled state, restart, model routing, live providers, publication and customer outcomes require their own observations. A hosted GitHub Actions result is evidence only when that exact run was authorized and observed; local checks do not impersonate hosted execution.
