# Omnara documentation accessibility review

Verdict: PASS WITH BOUNDED EVIDENCE

Reviewed content commit: f5b480c75b929a6fd93b62c13df2c93d7f80b956
Documentation fingerprint: 44e15e9cc9b3ed60b4f87cf628a86ab859fede339cab566d0cb4835ee48fd60b

Hesperos accessibility-oriented lint passed all 18 customer-facing Markdown documents after two directional phrases were replaced with explicit section links.

Rendered-source checks passed for six HTML documents: one H1 each; main and navigation landmarks; skip links; no missing image alt attributes; persistent mobile navigation; visible focus; reduced-motion support; and no motion-dependent content. All 89 local link and asset instances resolved.

Measured foreground/background contrast ratios:
- body 19.46:1
- muted 10.67:1
- cyan links 12.20:1
- amber labels 10.47:1
- focus indicator 14.03:1
- paper text 13.00:1
- paper muted 5.20:1
- paper links 5.47:1
- primary button 9.77:1

The meaningful Pages image has descriptive alt text. The README hero has meaningful Markdown alt text. The social card is described by Open Graph alt metadata and carries visible typeset text.

Boundaries: this review covers the exact files and source-level rendered contract. It does not establish every browser and assistive-technology combination, representative-user success, universal WCAG conformance, legal compliance, or the not-yet-deployed live bytes. Live routes must be rechecked after publication.

Any change to a fingerprinted file invalidates this receipt.
