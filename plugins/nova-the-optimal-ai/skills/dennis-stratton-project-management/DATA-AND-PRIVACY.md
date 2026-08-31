# Data and privacy

Dennis Stratton Project Management v0.3.0 reasons from project material that you intentionally make available. This may include roadmaps, repositories, plans, budgets, schedules, risks, incidents, decisions, team information, stakeholder communications, evidence, and project-control records.

The packaged runtime declares no network, credential, telemetry, account-integration, or cloud-storage dependency. The optional CLI reads and writes local files at the resolved project-record estate or explicit paths. It does not independently transmit them. This statement does not describe the host, model provider, operating system, repository service, backup software, synchronization tool, or other tools you use.

## Record-estate custody

Within Nova Emergent, Dennis resolves the estate from an owner-approved explicit `--store` or the exact `DENNIS_PROJECT_HOME` value injected by the sibling `$nova-operations` registry-backed launcher. The standalone home-directory fallback is disabled. The estate contains one canonical control record and a linked-record directory per project.

Treat the estate as potentially sensitive. Choose a location with appropriate operating-system permissions, backup, retention, and deletion controls. The package does not encrypt the estate, authenticate users, manage access control, synchronize copies, or securely erase data.

Minimize stored content. Reference authoritative source evidence by locator when possible. Do not copy credentials, private keys, tokens, recovery codes, payment credentials, unnecessary personal data, unpublished financial information, customer data, security details, personnel assessments, contracts, or protected communications into the estate merely for completeness.

Keep the estate outside Dennis packages, install directories, release trees, repositories, global skill roots, caches, temporary directories, upload sandboxes, and `.codex`. A chat response, preview, download, or attachment remains a draft or transport copy until it is deliberately placed under authorized custody. Updating or removing Dennis must not delete project state.

Adoption preserves the external source file, but it creates a new local copy in the estate. Confirm owner authority and the destination's data-handling suitability before running it. After adoption, decide which copy is canonical and prevent ungoverned dual writes.

Host and model-provider retention, training, regional processing, access, and security practices remain governed by their own settings and terms. Verify them for your environment before using sensitive project material.

See `SECURITY.md`, `TERMS-OF-USE.md`, and the release safety and privacy guide.
