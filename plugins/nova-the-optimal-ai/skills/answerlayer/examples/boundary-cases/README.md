# Challenge the answer, not just the file

Use the [decision scenarios](../../evals/decision-scenarios.md) to test narrow questions, cumulative evidence, conflicts, future effectiveness and unavailable sources. The expected outcomes are authored expert examples, not measured model success.

For executable local checks, run `python -B -m unittest discover -s scripts/tests -v` from the skill folder. The suite uses synthetic records and temporary directories, including preserving failed writes and rejecting linked snapshot roots. Run `python -B -m unittest discover -s workspace -p test_host.py -v` for actual loopback boundaries. Browser checks require the separate Playwright/Chromium test dependencies described in [the workspace guide](../../workspace/README.md); ordinary product use needs neither.
