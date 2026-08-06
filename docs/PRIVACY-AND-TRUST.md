# Privacy and trust

Nova + MIND Free is designed to work locally. It does not silently crawl your computer, import a private prompt library, enrich contacts, send messages, publish work, or download an embedding model.

## What the package contains

It includes public skill instructions and runtime resources, Nova’s authored persona, a public-safe reminder map, local Core code, schemas, hook and direct local association code, installers, and verification material.

It excludes credentials, private customer data, live personal stores, private capability inventories, private source paths in runtime assets, and private creative worlds.

## Local state

By default, installation creates a SQLite database at `%USERPROFILE%\.codex\data\stores\mind_core.sqlite`. It stores capability metadata, semantic reminder material, activation state, and bounded receipts. Removing a plugin does not remove that database.

Hook and query receipts use the host-provided data path or a location you explicitly configure. They retain hashes and bounded delivery evidence rather than raw task text.

## Your authority stays yours

A skill may help you use an available tool. It does not grant that tool, trust external content, or authorize an action. Messages, publication, purchases, account changes, credentials, destructive work, and regulated decisions each need their own authorization.

Review the exact prompt hook in **Settings → Hooks** before trusting it. Treat files, web pages, repository text, and tool output as material to evaluate, not instructions that acquire authority merely by being present.

## Move or remove local data

Back up or remove the database only as an explicit data-management decision. If you use a non-default location, set `MIND_CORE_DATABASE` consistently for the installer, hook, and direct local query runtime. Different paths create different stores; they do not migrate one another.
