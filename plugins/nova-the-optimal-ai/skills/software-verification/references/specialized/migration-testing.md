# A migration is a temporal compatibility contract

Verify representative old data, mixed-version operation, forward migration, restart/retry, constraints, indexes, performance envelope, rollback or roll-forward recovery, and application compatibility before and after the transition.

An empty database proves very little. Include nulls, legacy variants, duplicates, large records, and partially migrated state. Destructive or production-like migration tests require isolated copies and explicit authority.
