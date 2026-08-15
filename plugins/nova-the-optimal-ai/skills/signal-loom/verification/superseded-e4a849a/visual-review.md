# Visual asset review - Signal Loom

Receipt: `SIGNAL-LOOM-VISUAL-4b88d1e-20260812`

All three final files were opened and their actual pixels inspected. They are different files, compositions, and aspect ratios.

| Role | File | Dimensions | SHA-256 | Verdict |
|---|---|---:|---|---|
| README hero | `assets/signal-loom-readme-hero.png` | 1600x720 | `7f8c710124a7d277def62b997276a2bfb5a39f540f353ab57d2b001708a6d878` | PASS - wide evidence-to-story system, clear hierarchy, no embedded text, safe crop |
| Pages hero | `docs/assets/signal-loom-pages-hero.png` | 1200x800 | `188d9101651244b17d82b8dd0fa16916b51dfd469cc5665ed8efae5134daeeb7` | PASS - distinct Loomfile studio composition sized for the site column, coherent product identity |
| Social card | `docs/assets/signal-loom-social-card.png` | 1200x630 | `6446c77f285606f3468a22080fe8494e4de9989f9c1352d4de17e28413931fb2` | PASS - exact visible title `Signal Loom` and line `Evidence becomes a story without losing its threads.` remain legible in the safe center |

No blank areas, broken rendering, accidental transparency, incoherent artifacts, illegible text, or duplicate-role masquerading were accepted. README and Pages wiring pass locally; Pages Open Graph/Twitter metadata uses the social card. Live candidate assets remain pending deployment.
