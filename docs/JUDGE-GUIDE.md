# Install and test Nova: judge guide

If you have five minutes, install both plugins, take Nova's tour, and give Ludis the cartographer prompt in [`../START-HERE.md`](../START-HERE.md). This guide is the exact reference path and evidence map.

## Fast path

Requirements: a Codex client with local plugin-marketplace support and access to GPT-5.6. The contest path was exercised through Codex CLI 0.144.5 on Microsoft Windows 10 build 19045; other operating systems and Codex versions are not claimed as verified for this release.

Get the [public repository](https://github.com/Stunspot/nova-the-optimal-ai-mind) with GitHub's **Code → Download ZIP** and extract it, or clone it:

```powershell
git clone https://github.com/Stunspot/nova-the-optimal-ai-mind.git
Set-Location nova-the-optimal-ai-mind
```

Then run from the repository root:

```powershell
codex plugin marketplace add .
codex plugin add augment-of-mind@collaborative-dynamics-build-week
codex plugin add nova-the-optimal-ai@collaborative-dynamics-build-week
codex plugin list
```

The marketplace name is `collaborative-dynamics-build-week`. The expected installed selectors are:

- `augment-of-mind@collaborative-dynamics-build-week`
- `nova-the-optimal-ai@collaborative-dynamics-build-week`

Begin a fresh Codex task so discovery does not depend on an older task's context.

This is the no-build path. Judges do not need Python, a package manager, or generated artifacts to install and try the two plugin roots in this checkout. Python 3 is needed only for optional verification and bounded helper scripts.

## What to exercise

Use the four prompts in [`../demo/DEMO-PROMPTS.md`](../demo/DEMO-PROMPTS.md). They cover:

1. optional, low-pressure onboarding;
2. Ludis character craft and live choice;
3. integrated MIND judgment;
4. TestForge's evidence boundary.

For a negative routing check, ask:

```text
Use $nova. Rewrite “meeting moved to four” as a polite one-sentence message.
```

Nova should simply produce the sentence. A specialist roster, research expedition, game engine, or MIND coalition would be a routing failure.

## Inspect the visual tour

Open this local file in a browser:

```text
plugins/nova-the-optimal-ai/skills/nova/assets/nova-tour.html
```

The committed asset is the runtime artifact. It is self-contained and declares a content-security policy that blocks connections. The browser evidence checks desktop and mobile layout, keyboard-visible controls, route selection, step navigation, reduced-motion styling, and no-JavaScript meaning.

## Inspect the packages

Release artifacts:

- `release/augment-of-mind-1.0.0.zip`
- `release/nova-the-optimal-ai-1.0.0.zip`
- `release/SHA256SUMS`

Each ZIP contains one plugin root, not the repository's verification or submission material. The build uses sorted paths and fixed ZIP timestamps. Fresh-extraction validation is recorded alongside the package receipts.

Use [`../release/README.md`](../release/README.md) for archive scope and exact SHA-256 verification commands. The judge install path is the repository marketplace in **Fast path**; the ZIPs are the separately verifiable distribution artifacts.

## Read the proof in this order

1. [`../verification/verification-report.md`](../verification/verification-report.md) — decision and evidence boundary.
2. [`../verification/documentation-review.md`](../verification/documentation-review.md) — full Hesperos documentation and accessibility review.
3. [`../verification/traceability-matrix.md`](../verification/traceability-matrix.md) — requirement-to-evidence mapping.
4. [`../verification/risk-register.md`](../verification/risk-register.md) — residual risks and owners.
5. [`../design/CONTEST-ACCEPTANCE.md`](../design/CONTEST-ACCEPTANCE.md) — local green gates versus human/external gates.
6. [`../verification/source-import-ledger.json`](../verification/source-import-ledger.json) and [`../verification/transformation-map.json`](../verification/transformation-map.json) — source custody.

## Troubleshooting

- **Marketplace already exists:** run `codex plugin marketplace list`. If `collaborative-dynamics-build-week` points to the intended checkout, keep it. If it points elsewhere, remove only that entry with `codex plugin marketplace remove collaborative-dynamics-build-week`, then rerun `codex plugin marketplace add .` from the intended checkout.
- **Plugin already installed:** remove only the contest selectors with `codex plugin remove augment-of-mind@collaborative-dynamics-build-week` and `codex plugin remove nova-the-optimal-ai@collaborative-dynamics-build-week`. Reinstall them with the fast-path commands, run `codex plugin list`, and begin a fresh task. Do not remove similarly named plugins from another marketplace.
- **Tour cannot be opened by the model:** open the HTML directly in a browser. The browser-tested local visual fallback remains available; conversational behavior is tracked separately in the live matrix.
- **MIND is absent:** Nova should still work, but the fifteen-Faculty integration claim is intentionally unavailable.
- **Host warnings name another plugin:** evaluate whether the warning names this marketplace and package before attributing it to the entry.

## Support boundary

This contest build performs no authentication, external messaging, purchasing, contact scraping, or silent publication. It includes local scripts used by its skills; those scripts operate only when the corresponding workflow is explicitly run and remain subject to Codex's normal permissions.
