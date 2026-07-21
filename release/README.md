# Nova + MIND 1.0.0 release archives

This directory contains the two deterministic distribution archives for the contest candidate. Each ZIP has one top-level plugin directory and can be inspected without rebuilding the product.

| Archive | Contents | SHA-256 |
|---|---|---|
| `augment-of-mind-1.0.0.zip` | MIND 1.0.0: 147 files, one integrator, and fifteen Faculties | `a5b1224cafce295dd6a373a2687952cb95fe029df22e4c88461554928653b593` |
| `nova-the-optimal-ai-1.0.0.zip` | Nova 1.0.0: 296 files across twelve skill roots and plugin support files | `0a27043b541dd51ec5a1900b8642ce9ec1fcf231d945d12243c71ce87b7fd7f0` |

## Verify the downloads

From this directory in PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 augment-of-mind-1.0.0.zip
Get-FileHash -Algorithm SHA256 nova-the-optimal-ai-1.0.0.zip
```

Compare the output with [`SHA256SUMS`](SHA256SUMS). On a host with `sha256sum`, run:

```text
sha256sum -c SHA256SUMS
```

## Install and test

The no-build judge path installs from the repository's local marketplace, not directly from these ZIP files. Return to the [five-minute start path](../START-HERE.md) for the exact commands.

The hashes establish the bytes and topology of these archives. Installation, discovery, model behavior, and external contest actions have separate receipts in [`../verification/`](../verification/).
