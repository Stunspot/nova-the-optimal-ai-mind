# A contract is shared meaning, not matching syntax

Record request and response shapes, required/optional semantics, defaults, errors, ordering, versioning, idempotency, and compatibility windows. Test producer and consumer assumptions independently where possible.

Schema agreement can coexist with semantic breakage: units, timezone, pagination, nullability, error codes, and retry behavior often drift without a type mismatch. A contract test should fail when a real consumer would misinterpret the change.
