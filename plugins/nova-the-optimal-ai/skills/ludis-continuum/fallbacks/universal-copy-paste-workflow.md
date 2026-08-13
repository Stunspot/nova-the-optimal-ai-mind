# Copy-paste workflow

Use this only when the host cannot load the Ludis skill or run its files.

1. Keep the campaign ledger visible in the conversation and label every object with `id`, `status`, `visibility`, `authority`, `provenance`, `confidence`, `tenure`, links, asset references, and export eligibility.
2. Ask the assistant to produce separate GM and player projections. Never place both audiences in one artifact.
3. For a programmatic handoff, request a neutral folder plan containing handouts, JSON/CSV data, scene/grid/token metadata, supplied-asset filenames, and a loss report. Copy the returned text into local files yourself.
4. For Alchemy, request individual Character JSON plus the exact `{"characters": [...]}` bulk wrapper. Supply the system key explicitly; do not let the assistant infer mechanics.
5. For Foundry, prefer the neutral folder plan unless you can independently create, inspect, and test the module files. No copy-paste transcript establishes live VTT compatibility.
6. Review all player text, filenames, and manually assembled files before sending anything. Inspect or listen to every format and treat code as text without executing it. Record GM approval outside the chat under your own custody.

Mark filesystem capture, hashing, schema validation, deterministic ZIP construction, exact-byte approval, and target import checks `not_executed`. Never infer GM approval, artifact identity, or successful import from conversational output.