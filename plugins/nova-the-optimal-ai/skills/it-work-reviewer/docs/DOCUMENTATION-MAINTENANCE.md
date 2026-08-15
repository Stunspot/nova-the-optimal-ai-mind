# Maintain the documentation

This page defines how release owners keep Beryl IT Benchcraft documentation aligned with product truth.

## Ownership and scope

- Product version: Beryl IT Benchcraft v0.1.3.
- Documentation owner: the accountable release owner.
- Approval authority: the person authorized to publish or distribute the release.
- Canonical product sources: primary and reviewer skills, persona, schemas, validators, references, assets, examples, evaluation contract, release manifest, provenance, and build-side verification record.

## Review triggers

Review affected topics when any of these changes:

- skill name, activation method, or package layout;
- case schema, controlled status, or disposition;
- safety, data, privacy, credential, or authority rule;
- supported platform or embedded knowledge depth;
- validator command or output;
- evaluation contract or verified evidence boundary;
- installation behavior in a supported host;
- recurring user failure or support question;
- documentation filename, heading, or link destination;
- applicable accessibility policy or delivery format.

## Review cadence

Review the documentation at every release and after any safety-critical correction. If no release occurs, the owner should review volatile installation and verification claims before redistribution.

## Change procedure

1. Identify the reader task and affected topics.
2. Record the authoritative source and its version.
3. Update the smallest coherent topic set and all incoming links.
4. Preserve uncertainty where product truth remains untested or conflicted.
5. Run accessible Markdown lint and manual task-flow review.
6. Validate the release manifest and fresh ZIP extraction.
7. Record the new artifact hash, verification boundary, and approval.

## Retirement rule

Retire a topic when the product no longer supports its task, a newer topic fully replaces it, or the release it describes is no longer distributed. Preserve a clear replacement link or version note rather than leaving a silent dead end.

## Feedback handling

Classify feedback by the blocked reader outcome: finding, understanding, acting, recovering, accessibility, technical truth, or version applicability. Safety and data-custody defects receive immediate review. Repeated support questions are evidence that information scent or task flow may be failing even when the prose is technically accurate.

This package does not define an external feedback endpoint. Use the release owner’s established channel and preserve the report with the affected version.
