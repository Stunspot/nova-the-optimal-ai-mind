# Work a real device problem in Beryl IT Studio

Open `workspace/Open.cmd` on Windows or `workspace/Open.command` on macOS from the Beryl skill folder. Python 3 and a modern browser are required. **Start a case** asks for the device, reported symptom, and desired outcome. Unknowns can stay unknown. You can also open an existing native IT case or explore the clearly labeled teaching case.

## Move the investigation forward

Use **Device & problem** to record the actual error, trigger, onset, working functions, recent changes, and stakes. **Scope & data care** keeps relevant authority, hazards, backup state, and recovery-key needs beside the case. These facts guide the work; the app does not inspect your device.

In **Explanations**, enter a possible mechanism, what it predicts, what would weaken it, and the observations that bear on it. **Plan a test** links an observation to one or more explanations and records the expected difference, prerequisites, authority, and stop condition. The workbench places the selected test beside its rival predictions. Nothing is executed by the app.

**Observations & files** records reported, observed, measured, retrieved, or assumed information with source, time, and limits. You may attach an already available log, document, or photo up to 8 MB. Text logs smaller than 1 MB and common images preview locally when you edit that observation; other files can be downloaded. Material is stored privately with the case. No automatic diagnosis or document interpretation occurs.

After an actual test, use **Record observed result** in the workbench. Keep its observation source and basis. Revising a result retains the previous observation. **Record a change** distinguishes a proposal from an applied change and records authority, rollback, and the immediate result.

Use **Retest & outcome** to record the original conditions, duration, actual results, and adjacent functions. Declaring `verified-resolved` requires an original-condition retest, results, adjacent checks or a stated reason they do not apply, and a reopen condition. This is your recorded assertion, not independent repair certification. Later changes to the case basis mark earlier verification for reassessment.

Keep **Next useful move** current. **Download handoff** gives you readable Markdown for a Beryl conversation or technician: the original problem, evidence, explanations, tests, changes, retest, and next step. No message is sent. Supporting files are included in the separate workspace backup, not embedded in that handoff.

## Keep and resume your cases

Saved cases are selectable at the top of the app. Case actions save privately; read the save status. Windows defaults to writable local application data outside the installed skill. Launch with `--data-home "E:\My Beryl Cases"` to choose another writable folder. Existing native case imports become separate saved cases; the imported originals stay unchanged.

**Back up all cases** downloads the workspace with attached files. **Restore backup** adds copies and preserves existing cases. The workspace is limited to 200 cases and 40 MB; keep large originals separately and record their location. **Download copy** remains the compatible native IT case JSON export and excludes attached file bytes.

A malformed backup cannot replace saved work. If another window has saved a newer state, the older writer is refused: back up its current work, reload, restore the copy, and reconcile. If work.json cannot be read, preserve it and launch with a fresh writable data folder before restoring a known-good backup.

The three authored studio environments—Mossglass, Night Probe, and Cinder Relay—remain available. **Edit case JSON** is an advanced route for unusual native fields, not a prerequisite for ordinary investigation. **Check structure** reports native structure and bounded declared consistency; it does not authenticate a source, execute a command, establish authority, or certify a fix. Imported IT reviews remain separate attributed advisory records.
