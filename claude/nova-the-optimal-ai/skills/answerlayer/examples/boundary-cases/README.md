# Challenge the answer, not just the file

Use the [decision scenarios](../../evals/decision-scenarios.md) to test narrow questions, cumulative evidence, conflicts, future effectiveness and unavailable sources. The expected outcomes are authored expert examples, not measured model success.

For executable local checks, run `python -B -m unittest discover -s scripts/tests -v` from the skill folder. The suite uses synthetic records and temporary directories, including preserving failed writes and rejecting linked snapshot roots.

For a complete native walkthrough, follow [Your first local patch](../first-value/README.md), then ask the assistant to compare the retained baseline and adopted answer against the fictional evidence. The separate companion has been retired; its browser and loopback tests are historical material, not current installation requirements.
