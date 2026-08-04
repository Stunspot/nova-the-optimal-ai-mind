# Protect people, data, and authority

Read this page before acting on a problem involving heat, swelling, smoke, liquid, electricity, unstable storage, irreplaceable data, credentials, a managed device, or suspected compromise. Beryl can help recognize and document a boundary; it cannot make a physical hazard safe or grant authority.

## Stop at an immediate physical hazard

> **Warning:** Smoke, sparks, hissing, venting, fire, a burning smell, rapidly increasing heat, exposed mains wiring, or a damaged power supply can cause fire, shock, toxic exposure, or further damage. Do not continue an AI-guided diagnostic procedure. Follow local emergency guidance and transfer custody to an appropriately qualified person.

### Heat and case separation

Heat plus a separating laptop case is consistent with a swollen lithium battery and is a hard custody boundary.

- Do not continue charging or using the device.
- Do not press, cool, open, carry, photograph, inspect, disconnect, or power the device through user-led instructions.
- Use emergency response for smoke, hissing, venting, fire, or rapidly increasing heat.
- Use a qualified battery or device technician for model-appropriate isolation, handling, transport, and any later powered data access.

Prepare a handoff from facts you already know: device identity, observed heat or separation, important data, backup state, and encryption or recovery-key custody. Do not handle the device to obtain a missing fact.

### Liquid, mains, and internal power components

Liquid ingress, damaged mains wiring, live-board probing, CRT work, power-supply internals, exposed capacitors, battery-cell work, and board-level rework require appropriate equipment and physical competence. Ask Beryl for a handoff, not an execution recipe.

## Protect unique or valuable data

Treat clicking, disconnecting, intermittently visible, or otherwise unstable storage as a data-custody problem before a filesystem problem.

> **Important:** Do not run filesystem repair, benchmarks, malware scans, repeated copy attempts, or other write-heavy diagnostics on the original device when unique data may be recoverable.

For unique high-value data, the conservative default is professional recovery. Qualified minimal-read imaging is an alternative only when the media condition, data value, equipment, competence, and custody support it. Record the device identity, symptoms, connection history, data value, encryption state, and actions already attempted.

## Protect credentials and private information

Never paste any of these into a chat or case file:

- passwords;
- MFA codes;
- recovery phrases;
- private keys;
- full payment-card or identity documents;
- secrets copied from configuration files;
- encryption recovery keys unless an accountable recovery workflow specifically requires and protects them.

Use redacted excerpts and describe the secret’s type and location instead of its value. Confirm who owns the data and who may authorize access.

## Preserve organizational incident custody

An unknown remote-control tool, repeated MFA prompts, suspicious account activity, or security alerts on a workplace or school device may be a managed incident.

- Do not uninstall tools, erase logs, reset administrative credentials, or conceal changes.
- Contact the accountable support or security team through a separate trusted channel or device.
- Preserve exact alerts, times, device identity, network context, and actions already taken.
- Follow the organization’s containment direction. Disconnecting a device can preserve safety or destroy evidence depending on policy and architecture.

## Confirm authority before change

Authority is granular. Permission to inspect does not imply permission to access files, reset credentials, install software, replace parts, spend money, wipe a device, dispose of media, or declare the case complete.

Before a consequential change, identify:

- the owner or accountable administrator;
- the exact action authorized;
- the devices, accounts, data, and time window in scope;
- the expected consequence and rollback;
- the person who may accept residual risk or completion.

## Prepare a safe handoff

When work must transfer, include only information already available without increasing the hazard:

- device manufacturer, model, serial or asset identifier when known;
- exact observed symptoms and timing;
- hazard state and safe stopping state;
- important data and backup state;
- encryption or recovery-key custody, without exposing the key;
- ownership and authorized scope;
- actions already attempted;
- the qualified custodian needed;
- evidence required before work can resume.

Use `assets/device-intake-and-custody.md` or `assets/work-order-and-handoff.md` to preserve this information.
