# Beryl IT Benchcraft v0.1.0

Beryl IT Benchcraft is an IT technician capability for diagnosing, repair-planning, configuring, recovering, securing, migrating, and documenting computers and small networks. You describe the problem in ordinary language; Beryl turns it into a safe, evidence-led case with a useful next move and an honest completion state.

Use it for personal computers, supported workplace devices, operating-system problems, hardware decisions, peripherals, Wi-Fi and network faults, data protection, security concerns, migrations, repair quotes, and technician handoffs.

> **Warning:** Do not use an AI response as permission to handle swollen batteries, smoke, heat, liquid damage, mains electricity, unstable storage containing unique data, managed-device security incidents, or destructive recovery. Start with [Protect people, data, and authority](docs/SAFETY-AND-DATA.md).

## Choose where to start

| Your goal | Start here |
|---|---|
| Try Beryl on one problem | [Complete your first diagnostic turn](docs/QUICK-START.md) |
| Add the skills to a compatible host | [Install and confirm discovery](docs/INSTALLATION.md) |
| Understand the full working method | [Work an IT case with Beryl](docs/USER-GUIDE.md) |
| Preserve a long or consequential case | [Create, validate, and resume a case file](docs/CASE-FILES.md) |
| Recover when Beryl or the host cannot continue | [Troubleshoot Beryl IT Benchcraft](docs/TROUBLESHOOTING.md) |
| Check coverage and limits | [Capability matrix](docs/CAPABILITY-MATRIX.md) and [limitations](docs/LIMITATIONS.md) |
| Review a risky diagnosis or plan | Invoke `$it-work-reviewer` and read [Use independent review](docs/USER-GUIDE.md#use-independent-review) |
| Inspect package evidence | [Validation and evaluation](docs/VALIDATION-AND-EVALUATION.md) |

## Get a useful first response

Start a new task with the skill name and the problem:

```text
$beryl-it-tech My Windows laptop freezes after about 20 minutes on video calls. Audio keeps playing. It started after an update, and I need it for work tomorrow.
```

Include only what you know. Useful facts are the device and operating system, the exact symptom, when it happens, what still works, recent changes, and what matters most. “I don’t know” is valid evidence.

Beryl should return a compact problem frame, any immediate safety or data boundary, the leading explanations, and the smallest observation or test that can change the diagnosis. It should not pretend that a command ran, a device was inspected, or a repair worked without evidence.

## What the release contains

- `$beryl-it-tech`: the primary IT technician capability.
- `$it-work-reviewer`: an independent challenge for diagnoses, plans, handoffs, and completion claims.
- One unified Beryl practitioner identity.
- Progressive Windows, network, hardware, data, security, configuration, recovery, and service references.
- Case, intake, diagnostic, migration, work-order, and verification artifacts.
- Three worked examples and a ten-case behavioral evaluation suite.
- Standard-library validators for case files and release integrity.
- A universal copy-and-paste workflow for hosts without skill support.

## What the release does not provide

The package does not grant physical access, credentials, remote-management access, vendor portals, licensed tools, purchasing authority, organizational permission, or authorization for destructive changes. Exact firmware, drivers, compatibility, warranty, security, and version-specific procedures require current primary-vendor authority for the actual device and environment.

This package was built and validated as a release candidate. It was not installed into a target host during the build. Read [What was and was not verified](docs/VALIDATION-AND-EVALUATION.md#what-was-and-was-not-verified).

## Documentation map

- [Quick start](docs/QUICK-START.md)
- [Installation](docs/INSTALLATION.md)
- [User guide](docs/USER-GUIDE.md)
- [Safety and data custody](docs/SAFETY-AND-DATA.md)
- [Case-file reference](docs/CASE-FILES.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Capability matrix](docs/CAPABILITY-MATRIX.md)
- [Limitations](docs/LIMITATIONS.md)
- [Validation and evaluation](docs/VALIDATION-AND-EVALUATION.md)
- [Documentation accessibility](docs/ACCESSIBILITY.md)
- [Release notes](docs/RELEASE-NOTES.md)
- [Documentation maintenance](docs/DOCUMENTATION-MAINTENANCE.md)
- [Source provenance](PROVENANCE.md)
