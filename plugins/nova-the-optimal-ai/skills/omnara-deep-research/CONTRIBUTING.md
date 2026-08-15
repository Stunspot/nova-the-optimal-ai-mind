# Contributing

Contributions that improve research custody, documentation, campaign schemas, deterministic helpers, or bounded host portability are welcome.

Before changing code or doctrine:

1. open or reference an issue that states the customer problem and evidence boundary;
2. preserve canonical inquiry-engine custody and provenance;
3. do not turn optional services, paid access, private sources, or unsupported hosts into silent requirements;
4. keep source assertions, observations, deterministic results, inference, synthesis, and speculation distinct;
5. update customer documentation when behavior, fields, installation, privacy, or limitations change.

Run before proposing a change:

~~~shell
python -B scripts/validate_release.py . --profile source
python -B -m unittest discover -s tests -v
~~~

For helper changes, include a minimal reproducible campaign fixture or test. For documentation changes, exercise local links and read the rendered result. Do not include confidential campaigns, copyrighted source dumps, credentials, generated caches, or unrelated work.

By contributing, you agree that your contribution may be distributed under the repository's [MIT License](LICENSE.md).
