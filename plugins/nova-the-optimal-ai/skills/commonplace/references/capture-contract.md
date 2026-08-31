# Capture and epistemic contract

A capture records selected text or a source packet and the user's reason for retaining it. Raw/binary source bytes remain with the source owner. Assertions inferred from the saved material are separate records or explicitly derived claims.

The canonical record carries stable record id/revision, timestamps, content, state, sensitivity, rights, provenance, and relations; its selected snapshot supplies workspace/generation binding. Mutation authority is digested in the snapshot transaction rather than stored as normalized actor text. A sourced capture records a locator and may record title/author metadata, retrieval time, selected-text span/quote, note, and source content digest.

State axes remain orthogonal:

- origin: user_authored, quoted, reported, model_inferred
- review: unreviewed, accepted, verified
- dispute: undisputed, challenged, contradicted
- lifecycle: current, superseded, retracted
- sensitivity: public, personal, private, restricted
- rights: self_authored, quoted_excerpt, licensed, unknown

Verified requires named supporting evidence; it does not follow from repetition or model confidence. Contradicted does not automatically select a winner. Supersession changes which revision is current without erasing the prior record. Retraction withdraws a record without claiming it never existed. Forgetting is a separately planned purge across canonical and derived custody.
