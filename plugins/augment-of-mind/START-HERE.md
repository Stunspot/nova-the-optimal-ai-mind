# Install MIND

MIND is a standalone cognitive architecture for an existing AI harness. It adds sixteen cognitive Faculties, integrated mission control, local semantic capability reminders, Capability Promotion, and the two-part TestForge verification gate.

## The normal installation

1. Give the MIND package to a compatible Codex harness.
2. Ask the harness to install and enable **MIND by Collaborative Dynamics**.
3. Review the file operations and configuration changes it proposes.
4. Open **Settings → Hooks**, inspect the exact local MIND prompt-submit hook, and decide whether to trust it.
5. Start a new task so Codex can discover the plugin.

Installation is complete when MIND is enabled, its Faculties are discoverable in a new task, the reminder estate reports active, and the trusted hook can reach the configured local `qwen3-embedding:0.6b` endpoint—or names the exact dependency that remains unavailable.

## Manual fallback

If your harness cannot install an attached package, extract it and follow [Manual Codex installation](INSTALL-CODEX.md).

## What you installed

MIND is one integrator, sixteen Faculties, Capability Promotion, and two TestForge skills. It coordinates cognition; it does not impersonate every occupational specialist or grant tools and permissions the host does not have.

Read [Capabilities and limits](CAPABILITIES-AND-LIMITS.md) for the complete shape and [Use MIND](USER-GUIDE.md) for its operating model.
