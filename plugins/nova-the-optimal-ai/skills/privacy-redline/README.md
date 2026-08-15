# Privacy Redline runtime skill

This is the self-contained installable runtime for Privacy Redline v0.1.1. Start with `SKILL.md`. The five canonical personas, five canonical knowledge bases, and five canonical prompt omnibuses are preserved as exact runtime copies and loaded selectively by responsibility.

Run the local structural checks from this directory:

```powershell
python -B scripts/self_check.py
python -B scripts/privacy_case_guardrail.py examples/redline-session/case.json
python -B -m unittest discover -s scripts/tests -p "test_*.py"
```

These checks do not establish legal correctness, device security, successful installation, natural-language activation, or behavioral competence.

