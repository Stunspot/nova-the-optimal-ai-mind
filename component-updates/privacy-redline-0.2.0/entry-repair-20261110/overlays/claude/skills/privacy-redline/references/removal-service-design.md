# Design for a personal removal service

Use this design for an explicit request to engineer, assess the implementation of, or commission a removal-service product. A personal request such as “can you do an Incogni thing for me?” starts discovery and removal assistance in personal-data-removal.md. Continuing that personal work over time remains a user workflow; this reference supplies engineering requirements only when an actual service implementation is at issue. The current skill supplies judgment and host-assisted work. Engineering and qualifying the following runtime establishes a standing service.

## Start with one person's outcome

The user starts by stating a privacy concern or asking for cleanup. The service discovers likely exposure, asks progressively for necessary facts, explains useful findings, and prepares concrete actions. The person makes choices about what to preserve, approves bounded disclosures and directly completes protected-field or identity steps. Show changes and unresolved work in ordinary language. Specialist routes, policy interpretation and internal records support this interaction backstage.

Ship a single-user local runner first. Help the person reduce harmful public identity links and exercise appropriate deletion or suppression rights. Show the exposed result, its practical risk, the proposed action and its actual outcome. Keep technical evidence available behind those actions. Measure false matches, disclosure required, verified reduction, recurrence and user intervention alongside coverage. A high request count alone says little about protection.

A small maintained provider set is an honest first release. Provider coverage means a current, exercised request and verification path for that route, including its supported jurisdictions and exceptions. A list of broker names establishes discovery coverage only. Private database requests remain useful without public proof that the person has a record.

## Separate access by responsibility

| Component | Inputs and authority | Boundary |
|---|---|---|
| User-controlled profile vault | Identity attributes and protected locators supplied directly by the user | Encrypt at rest using maintained platform facilities, enforce local access, define retention, backup and deletion |
| Public provider directory | Official operator, policy, processor delegation, route version and required field categories | Contains no customer identities |
| Discovery worker | Approved minimum search anchor and target scope | No general vault access or submission privilege |
| Evidence reader | Untrusted source material and redacted facts | Model can propose actions and interpret evidence |
| Grant store and validator | User-approved recipients, purpose, data categories, duration and recurrence | Reader cannot create or enlarge grants |
| Submission worker | Valid grant, qualified route and opaque field references | Resolves values just before use and enforces destination and payload constraints |
| Outcome checker | Protected target reference and expected effect | Reads only what is needed to assess the named result |

A local application may still disclose information to model, browser, search, email and target providers. Document the real routes. Separate discovery-only sessions from authenticated submission sessions. Keep tokens, personal URL segments, snapshots, crash reports and browser recordings out of general logs and model prompts. Default telemetry should carry no identity data.

Store each subject's data separately even in the single-user design. A future hosted product needs separately qualified tenant isolation, administrative access, abuse response, legal agency, breach response and secure deletion across backups. Defer that expansion until its risks and operating owner are established.

## Qualify a provider adapter

Bind a route to its official evidence, exact HTTPS origin and path constraints, delegated form processors, request type, field mapping, applicable region, authority requirements and observed behavior. Keep provider changes versioned. A directory entry is evidence of a qualified route, not a user's consent.

At execution, validate the resolved destination and payload against that binding. Reject unexpected redirect targets and private, loopback, link-local or metadata endpoints. Prevent DNS rebinding and cross-origin credential forwarding in the fetch layer. Browser automation needs navigation and network controls that actually enforce the same limits, including outbound subrequests and form actions. If those controls are unavailable, expose a direct user handoff instead of claiming constrained automation. A new required field or changed action needs renewed qualification.

Use supported public and authenticated processes. Rate-limit by operator, honor provider backoff and stop on access challenges. Keep CAPTCHA, required identity proof and signing steps available for the user. Avoid automatic uploads of identity documents. An adapter cannot infer agency from possession of identifiers.

## Bind consent to the actual operation

A grant identifies the subject, recipient set, request purpose and type, permitted field categories, data revision, route version, approval time, expiration, recurrence and revocation state. Let the person review actual values in a secure local preview. Changes that alter recipient, purpose, disclosed data or consequences require a new grant. Nonmaterial adapter repairs can preserve a grant only when the unchanged scope is demonstrated.

A recurring grant can cover a specified provider set and recheck cadence. Adding a provider or changing purpose needs coverage from the user's grant. Withdrawal atomically disables queued and future dispatches. Disclose that already-dispatched data cannot be recalled. Account deletion and legal attestations have distinct consequences and must be separately scoped.

Before resolving sensitive values, the executor checks the current grant and qualified route. The single dispatch authority rechecks revocation immediately before committing a send. That commit is the local cutoff. Cancellation before it prevents dispatch, while cancellation racing or following it produces possibly sent status until reconciled. No atomic cancellation across the remote provider is promised. Limit payload construction to the approved fields. A prompt, search result, email or broker response can never mint a grant.

## Preserve uncertainty through failures

Track authority, delivery and outcome separately. A useful delivery sequence is prepared → dispatching → submitted → acknowledged, with explicit rejected and unknown branches. Outcomes include observed listing absent, broker-reported deletion, suppression, exemption, no record found, unchanged, recurrence and unknown. These outcomes can coexist across distinct targets.

Use a durable transaction to claim a request and mark possible dispatch before network I/O. Enforce one active attempt per subject, operator and purpose. Route all outbound writes through one dispatch authority that validates an immutable command containing subject reference, grant revision, route revision, purpose, permitted fields and attempt ID. A database lease alone cannot fence a remote HTTP request. The dispatch authority must reject stale fencing tokens and prohibit takeover from reissuing an unresolved command. A timeout or crash after dispatch moves the item to reconciliation. Query supported status or inspect an official receipt before retrying. Where the provider supplies no idempotency or status mechanism, preserve unknown delivery and use a human resolution path.

Use provider idempotency keys when supported and keep their scope explicit. Retried writes after a definitive pre-dispatch failure still recheck the current grant and route. Cancellation stops pending work. Completion, cancellation and revocation races need real concurrency tests at the dispatch boundary.

## Verify protection and remain usable

Bind an observation to the matched subject, locator, environment, time and check method. A successful HTTP request does not prove removal. A blocked, empty or failed page cannot establish absence. When checking public disappearance, require a healthy retrieval and test that the result is specific to the intended record. Use independent corroboration when the consequence justifies it.

A receipt-only acknowledgment establishes delivery, with the outcome pending or unknown. An explicit completion statement establishes only the stated broker-reported deletion or suppression, with its scope, exemptions and partial fulfillment. Neither establishes independently verified internal erasure. An opt-out can be successful while data remains stored. A recurrence check revalidates identity. Keep the next action visible when verification is blocked.

A dedicated response mailbox may reduce access scope. Use per-service aliases when accepted, and let the user choose the tradeoff. Read only case-relevant messages, isolate verification tokens and validate action URLs against the qualified route. Revocation covers mailbox polling and scheduled checks as well as submission.

Recovery should restore encrypted profile and grant state without reviving revoked work. Restoring an older backup requires reconciliation against newer revocations or a fresh user grant. Exit disables scheduled work, releases permissions and lets the person export or delete their data with clear backup-retention consequences.


## Minimize retained sensitive state

Keep identity values and identifying locators only while they support a user-authorized active purpose. Let the person inspect and delete them. Define a retention setting during onboarding, with review at case closure and grant expiry. Expire verification links and tokens after their use or provider expiry. Keep only redacted request IDs, purpose, status and observation references needed to reconcile unresolved work.

Use ephemeral browser profiles for discovery and scoped authenticated profiles for submission where the provider permits it. Inventory history, cookies, cache, downloads, recordings and screenshots as potential copies. Disable unnecessary capture and redact necessary evidence at collection. Inspect host and model-provider retention independently of local disk encryption.

Make backup retention explicit. Expiring local data must expire eligible backups through the supported lifecycle. Explain any retained recovery window. An export is another copy under the user's custody. Secure deletion claims require evidence for the storage and backup layers involved. Keep revocation tombstones or require fresh authority after restore so deleted operational history cannot silently revive an old grant.

## Build and test in stages

First prove discovery, semantic analysis and matching with synthetic and supplied redacted examples. Then qualify one provider's supported workflow using a consented test case. Add submission only after vault isolation, destination enforcement, payload minimization, grant validation, timeout recovery and revocation work through the normal entrypoint.

Exercise namesakes, copied records, empty searches, private records, stale legal guidance, misleading labels, injected instructions, lookalike origins, delegated forms, redirects, DNS changes, new fields, CAPTCHA, uncertain POSTs, overlapping workers, revoked grants, old backups and unavailable verification. Include legitimate authorized completion as a required case. A system that holds every request has failed its purpose.

Expand provider coverage only as adapters pass those checks. Enable scheduled recurrence only when the person grants it and the runner survives interruption and cancellation. Report measured coverage and observed outcomes, with live effectiveness evaluated separately from fixture success.
