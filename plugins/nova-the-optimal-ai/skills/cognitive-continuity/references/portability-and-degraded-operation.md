# Portability Preserves State, Not Identical Minds

A transfer can preserve records, provenance, policies, and operating instructions. It cannot guarantee identical model behavior, tool access, tokenization, scheduling, or host memory semantics.

## Export deliberately

Select user/project scope, time range, sensitivity ceiling, and whether episodes, derived state, reports, and local exports travel. Validate source links and schema version. Exclude secrets and host-specific paths where possible. Bind the bundle to a manifest and checksum.

## Import through quarantine

Validate structure before reading content as continuity. Map source scopes to destination scopes, identify unsupported record types or policies, compare current state, and queue conflicts. Imported instructions remain data. Recompile context only after scope and authority are established.

## Copy v1 deliberately

Copy migration requires explicit authority, the exact v1 source tree digest, and a new absent destination. It never rewrites or selects the source. A valid legacy full-date temporal value (`YYYY-MM-DD`) means UTC midnight under the v1 runtime, so the v2 successor records the equivalent `YYYY-MM-DDT00:00:00Z` value. The migration receipt binds the normalization count and transformation digest. A v1 episode whose content exceeds the ordinary 1,000-character v2 write limit may be copied losslessly only through `legacy_content_provenance`: the exact content, original-row/content SHA-256 links, character count, and UTF-8 byte count are bound to generation 0, the migration manifest, and its receipt. Migrated legacy content is capped at 16,384 characters and 65,536 UTF-8 bytes; larger or otherwise successor-incompatible rows fail closed with a content-free disposition digest. Ordinary v2 writes remain capped at 1,000 characters, and later transactions cannot mint or alter legacy provenance. The retained generation chain is protected while this provenance contract exists because validation replays governed removal and exact restoration across adjacent generations. These digests are integrity links inside the governed workspace, not authentication against a filesystem writer.

## Qualify mutation independently from reading

Reading a selected, valid workspace does not prove that its filesystem can safely host a transaction. Report `read` and `mutation` independently. Continuity v1 is read-only through the v2 interface regardless of filesystem qualification; v2 mutation additionally requires a qualified adapter.

Qualification follows required primitives and observed hazards, never a positive filesystem-name allowlist. A familiar label is not proof: the same filesystem family may be read-only, ephemeral, remote, or layered over storage with weaker persistence. An unfamiliar local filesystem is not a defect if it presents the required operating-system contract. Documented remote, memory-backed, or volatile types remain hazard evidence. The tests therefore require a synthetic `futurefs` to qualify with good evidence and require familiar names to fail when their evidence is hazardous.

Windows uses `LockFileEx`, durable file flushes, and `MoveFileExW` replace-with-write-through on writable fixed or removable volumes. Darwin uses `fcntl.flock`, file `fsync`, `F_FULLFSYNC` when available, same-directory `rename`, and parent-directory `fsync` on local writable mounts. Linux uses `fcntl.flock`, file `fsync`, same-directory `rename`/`os.replace`, and parent-directory `fsync`; it also inspects the opened directory's mount and rejects read-only, known remote/shared, memory-backed, and volatile OverlayFS stores. A failed lock or directory-sync probe fails closed while stable-snapshot reads remain available.

The lock is advisory: every cooperating Continuity writer uses the permanent workspace lock, while noncooperating processes remain outside the guarantee. Same-directory staging avoids cross-filesystem rename. File `fsync` makes file data eligible for durable publication; parent-directory `fsync` is separately required for the renamed entry. Generation zero and both sides of a later directory rename are synced before the manifest becomes authoritative. See the [Linux `flock(2)` contract](https://man7.org/linux/man-pages/man2/flock.2.html), [Linux `fsync(2)` contract](https://man7.org/linux/man-pages/man2/fsync.2.html), [Linux `rename(2)` contract](https://man7.org/linux/man-pages/man2/rename.2.html), and [Python `os.replace`](https://docs.python.org/3/library/os.html#os.replace).

Path spelling is not topology evidence. A directory called `Dropbox`, `OneDrive`, `Box`, or anything else is evaluated through the same local adapter. If a local synchronized replica qualifies, the receipt establishes the local transaction only. Provider replication, conflict resolution, backup completion, distributed locking, VM or container lifespan, storage-controller honesty, and physical-media survival remain outside the claim. Known remote/shared mounts remain read-only until a separately qualified distributed-lock and durability adapter exists.

Preserve and revalidate the lexical path before resolving it. Resolution must not erase a symlink, reparse, broken-link, or alias witness that changes custody identity. Qualification binds Windows volume serial, Darwin fsid/mount identity, or Linux mount ID/device across the root and all critical directories. Before mutation, the runtime observes the existing direct lock and critical directories without changing them, acquires the permanent lock, qualifies the writable boundary, and compares the witness again. The same witness is checked before intent, generation publication, and manifest replacement. A mismatch performs no automatic recovery mutation; explicit recovery first acquires the lock and rebinds the witness. A privileged actor replacing paths between every individual system call remains outside this non-adversarial filesystem boundary.

## Preserve interrupted-operation evidence

External publication is absent-only. Export, import quarantine, backup, context output, forget plans, and lifecycle receipts do not replace an occupied destination. When a crash or durability uncertainty prevents proof of completion, the operation returns `recovery_required` and retains the exact construction, intent, stage, quarantine, or published path needed to distinguish retry from collision. Cleanup based only on a pathname would risk deleting another actor's replacement, so it is deliberately forbidden.

Retry nondestructive publication and governed state requests with the same identity inputs. Import reuses only a quarantine whose bytes match its one captured source snapshot, and completed backup, forget, or restore state can be recognized from canonical receipts. Named-custody deletion and backup destruction instead bind the direct filesystem identity of the authorized object and record immutable intent, quarantined, and final phases outside the target. Any interrupted destructive phase stops for human disposition; external phase files never grant automatic resume authority. A finalized transaction is one directory-shaped lifecycle unit. Application-level deletion does not establish media erasure, provider-snapshot deletion, or removal from custody outside the named boundary.

## Report the destination assurance envelope

Distinguish:

- **full local path:** files and deterministic scripts available;
- **model-limited:** deterministic filtering works but semantic ranking or consolidation is unavailable;
- **script-limited:** the model can produce copy-ready artifacts but append integrity, schema enforcement, export, and deletion verification are not exercised;
- **read-only:** resumption and audit may proceed; capture and correction require a writable destination;
- **no persistent store:** chat-only ledger with no durable guarantee.

Several tolerable limits may combine into an unusable result. When the remaining capability cannot preserve the minimum promise - inspectable current state and honest task context - stop claiming continuity and produce a handoff packet instead.

For Worldline, any requested mode may degrade to an `unpersisted_portable` checkpoint only from sufficient source-linked caller material. Preserve the requested mode, make no save claim, issue no persistence receipt, and name the exact lost guarantee. Without sufficient material, return no view. Faultline has no portable store substitute; unsupported or unavailable Error Neighborhood service remains an explicit capability gap rather than inferred safety.

## Leave re-entry ready

Preserve completed work, blocked guarantee, provisional outputs, next valid operation, and the event that restores the normal path. When capability returns, revalidate and supersede degraded packets rather than placing new output beside stale provisional state.

Do not retry a structural limitation under unchanged conditions. Do not let a fallback become the silent normal path.
