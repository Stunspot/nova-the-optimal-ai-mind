# Release requirements

The release may read records only after tenant authorization is checked at the request boundary.

The cross-tenant authorization invariant is: a caller may never retrieve, cite, summarize, or export a record belonging to another tenant unless an explicit delegated grant covers that exact operation.

Tests must exercise both authorized access and denial. Cache keys, retrieval indexes, logs, and context packets must preserve the same tenant boundary.
