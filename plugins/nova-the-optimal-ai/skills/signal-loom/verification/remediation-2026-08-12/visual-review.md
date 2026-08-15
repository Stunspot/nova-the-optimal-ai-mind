# Visual review

Date: 2026-08-12
Presentation fingerprint: 45304a55badd865ed48bc1d6bcef3ee321ec422e6b24efba47863ea693634c34
Verdict: PASS for all three final pixel files.

| Role | File | Size | SHA-256 | Pixel verdict |
|---|---|---:|---|---|
| README hero | assets/signal-loom-readme-hero.png | 1600x720 | 553f51af407c5eb37fd99b9e4cd9906c124d3f720553f8962cb2fb74828557fc | PASS - wide loom/press scene turns reports and data into a finished infographic; no embedded title; safe central composition |
| Pages hero | docs/assets/signal-loom-pages-hero.png | 1200x800 | 1a5cf0d578fd9df395e74525c4df7d4accc2e4ba84425886d762980edcc6ee69 | PASS - distinct overhead editorial worktable; hands assemble an infographic from evidence cards; no required text |
| Social card | docs/assets/signal-loom-social-card.jpg | 1200x630 | 7ecdf0f2dfbe1144e86d5401d72e49088717cfbd6fe3c1c15406b867d99444b7 | PASS - deployable 209 KB JPEG faithfully preserves the inspected poster composition; exact title 'Signal Loom' and line 'Makes source-bound infographics from research and data.' remain large, spelled correctly, high contrast, and crop-safe |

The three source compositions were opened and inspected after resizing. The deployable social JPEG was decoded and compared against the inspected lossless PNG source at the same 1200x630 dimensions; sampled mean absolute RGB error is 4.85/255 per channel. No blank field, clipping, incoherent artifact, illegible required text, or interchangeable dark-tech wallpaper remains.
