# Demonstration: Correction Changes Current State Without Rewriting History

An existing `user_model` record says “Ship to 10 Old Road,” sourced to `EP-OLD`. The user says, “Correction: use 22 New Street from now on.”

The Agent appends the correction episode first. Because the current user owns this personal state and the request is explicit, it records a new current `user_model` record that supersedes the old one and returns a receipt.

The old record becomes `superseded` with a valid-to time. It remains reachable for historical questions but is ineligible for ordinary current context. A new shipping task receives only 22 New Street as current state. Recent episode chronology, if included, is labeled source-only.

**Governing cue:** The time an old assertion was recorded does not let it compete with a later valid user correction. Correction preserves provenance; forgetting removes content.
