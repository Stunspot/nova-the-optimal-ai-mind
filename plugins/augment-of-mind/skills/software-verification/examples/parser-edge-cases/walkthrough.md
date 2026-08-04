# Parser edge-case walkthrough

This synthetic project demonstrates the conditional compiler/parser branch, token-boundary reasoning, metamorphic opportunity, malformed-input caution, and a deliberately bounded claim.

From this example directory:

```text
python -m unittest expected.test_parser -v
```

The escaped-delimiter cases fail while the unescaped normal case passes. `expected/execution-record.json` preserves the actual failing command record. The manifest does not pretend the examples establish a complete grammar: consecutive escapes and malformed forms remain residual risk pending parser-owner authority.
