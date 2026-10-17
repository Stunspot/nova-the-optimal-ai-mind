# Demonstration: load compiler reasoning only when representation becomes behavior

Load when a parser, DSL, protocol decoder, or transformation pipeline changes.

The visible symptom is “escaped semicolons break.” TestForge separates lexical boundary from value decoding. The decisive cue is operation order: splitting occurs before the parser knows whether a delimiter is escaped.

That cue produces a concrete invariant—only unescaped semicolons separate pairs—and a minimal scenario that preserves the escaped delimiter while still recognizing the next real pair. A second property-shaped example checks semantic preservation across backslashes and delimiters. The full escape grammar remains unresolved because the supplied contract does not define every consecutive-backslash case.

The executed tests establish the planted defect, not a complete grammar. The report remains `NOT_READY`, and the parser owner must define the broader grammar before a generalized repair can be called correct.

The transferable behavior is to locate the representation boundary, test a property of meaning, and keep the unprovided grammar outside the claim.
