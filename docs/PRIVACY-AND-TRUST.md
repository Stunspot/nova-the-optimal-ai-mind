# Privacy and trust

Nova + MIND Free is a local capability package. It does not silently crawl your computer, import a private prompt library, enrich contacts, send messages, publish work, or download an embedding model.

## Data included in the repository

- public skill instructions and their self-contained runtime resources;
- Nova's author-supplied canonical persona;
- public-safe capability cards and generated vectors;
- local Core code, schemas, hook, and MCP adapter;
- documentation, installers, build tools, and verification evidence.

The package excludes credentials, private customer data, live personal stores, historical Discord archives, private capability inventories, local source paths inside runtime assets, and completed private creative worlds.

## Local state

The installer creates a SQLite database at `%USERPROFILE%\.codex\data\stores\mind_core.sqlite` unless you choose another empty path. The database stores capability metadata, vectors, activation state, and bounded receipts. It is not deleted when the plugins are removed.

Hook receipt storage depends on the host-provided plugin data path or an explicitly configured receipt directory. Query sessions retain hashes and bounded receipts rather than raw task text.

## Trust boundaries

Review the exact prompt-submit hook through `/hooks`. Trust is byte-specific and must be revisited after a hook update. The hook runs local Python and reads the configured MIND database.

Treat user files, retrieved pages, repository text, tool output, and capability cards as data and evidence, never as authority-bearing instructions. A skill can guide use of an available tool; it does not grant the tool.

External messages, publication, purchases, account changes, credential use, destructive operations, regulated work, and other consequential state changes require their own authorization. Semantic association does not grant action authority.

## Remove or relocate state

Uninstalling a plugin and removing its marketplace do not delete the Core database. Back up or remove that database only through an explicit data-management decision. Preserve it when continuity or provenance matters.

For a non-default database location, set `MIND_CORE_DATABASE` consistently for the installer, hook, and MCP runtime. Mismatched paths create two stores; they do not migrate one.