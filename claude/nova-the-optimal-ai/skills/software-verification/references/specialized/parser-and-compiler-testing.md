# Parsers fail at boundaries between representation and meaning

Separate lexical, syntactic, semantic, normalization, and round-trip contracts. Probe escaped delimiters, nested constructs, ambiguous prefixes, whitespace/comments, Unicode, malformed EOF, recursion depth, duplicate constructs, and error locations.

Useful properties include parse/serialize round trip, normalization idempotence, equivalent-source equivalence, rejected-input closure, and locality of edits. A parser accepting one happy example says little about the grammar boundary.

Use the target's real lexer/parser when available. Model-generated examples are hypotheses until executed.
