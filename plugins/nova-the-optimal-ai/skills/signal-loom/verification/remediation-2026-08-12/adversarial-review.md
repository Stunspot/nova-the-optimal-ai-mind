# Adversarial verification

Date: 2026-08-12
Candidate fingerprint: 4105d1b5f579cf58f0a6d696f69965f87ba2d136b40f8af1bc486b1c777f9a85
Documentation fingerprint: 3cbcc1d89347d6fc04727736cd173007f2ac0564d9dce9d684b8b5b24233defd
Presentation fingerprint: 45304a55badd865ed48bc1d6bcef3ee321ec422e6b24efba47863ea693634c34
Verdict: PASS_LOCAL with post-deployment rendered verification required.

Challenges and results:

- Product buried: repaired. The README opens with **Signal Loom makes infographics** and immediately names inputs and output.
- README exists but does not orient: repaired. A visitor can now identify fit, install, prove discovery/invocation/health, make a first infographic, recover, and find deeper guidance without reading an internal verification narrative first.
- Wide viewport or browser zoom collapses content: repaired in source. The outer content width no longer combines a fixed cap with viewport-growing internal padding. The focused regression rejects the exact failed rule.
- Narrow viewport: source geometry retains a 1rem gutter and mobile grid breakpoints; the computed content width is 288 pixels at a 320-pixel viewport.
- Unsupported capability inflation: rejected. The README preserves manual publication, evidence authority, static-check, security, accessibility, and factual limits.
- Broken navigation: rejected. Local file and same-page fragment checks pass; both HTML files pass bounded inspection.
- Social delivery format: repaired. The accepted 1200x630 JPEG is 209 KB, the Pages source metadata names it twice, and a regression rejects a return to the 1.83 MB PNG source master.

Fourteen unit tests, package self-check, both HTML inspections, eight Hesperos lint passes, local link/fragment checks, exact TestForge line-ending verification, and diff hygiene pass. The remaining decisive check is the corrected live render in the browser state that produced the screenshot.