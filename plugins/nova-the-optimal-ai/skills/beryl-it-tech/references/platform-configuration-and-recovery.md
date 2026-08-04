# Read the state transition, not the operating-system logo

## Route by phase

Boot and recovery failures become tractable when localized: power-on/POST → firmware/UEFI → boot selection → loader → kernel/drivers → services/identity → shell/session → application. Ask what is the last reliably observed phase and what changed nearby.

For performance, separate utilization, saturation, errors, latency, and contention. A high percentage is not automatically a fault; low average use can hide bursts. Compare a baseline under the same named workload and timing, including the smallest relevant set of CPU, memory, storage, network, thermal, error, free-space, update-state, and recent-change observations. Inspect the subsystem that owns the delay.

For updates and drivers, preserve build/version, source, prior state, device ID, change time, and rollback viability. Prefer vendor/OEM or OS-native sources matched to hardware and build. Treat generic “driver updater,” registry cleaner, and debloat bundles as uncontrolled multi-variable interventions.

## Windows depth

Load `../knowledge/windows-systems-engineering.md` for Windows internals, boot, identity, networking, servicing, and advanced observation. Favor Event Viewer, Reliability Monitor, Resource Monitor, Task Manager, built-in troubleshooters, DISM/SFC in the correct order and context, ProcMon, WPR/WPA, and dump analysis according to the question. A tool is useful when its observation can change the branch.

Respect the component store, ACLs, encryption, Secure Boot, recovery keys, and organization policy. Avoid manual registry/service surgery until the failed subsystem and rollback are understood.

## Firmware applicability gate

Do not infer a firmware fault from a chipset family, board marking, or update request, and do not invent an unreported boot state. Before naming a file or execution procedure, require the exact manufacturer, product model, hardware revision, current firmware version, installed CPU, reason the change is needed, and the matching current primary-vendor procedure. Preserve stable power, backed-up data, encryption/recovery-key custody, current settings where useful, and the model-specific recovery method. If identity or applicability is incomplete, leave a plan-ready source request and a safer diagnostic branch; never trial-flash candidates.

## macOS and Linux routing

Use the same phase/layer model while translating to platform-native authority and tools. On macOS, preserve model/chip, macOS version, FileVault/recovery, Apple diagnostics/recovery mode, APFS state, profiles/MDM, and supported Apple procedures. On Linux, preserve distribution/release, kernel, bootloader, init/service manager, package source, filesystem, desktop/session, permissions, and logs. Do not transplant Windows commands or assumptions.

## Rebuilds and migrations

A clean installation is a controlled migration, not a diagnostic eraser. Inventory data, applications, licenses, accounts, encryption keys, drivers, accessibility settings, browser/email state, and external dependencies; create and test backup; prepare trusted media; define rollback; validate data and required workflows after cutover.
