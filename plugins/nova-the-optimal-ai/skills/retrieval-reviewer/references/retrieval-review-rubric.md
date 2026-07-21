# Retrieval review rubric

## Identity and custody

- Is the corpus root and revision identified?
- Does the index identity correspond to that corpus state?
- Are source paths, line ranges, source hashes, and chunk IDs present and resolvable?
- Are the actual query, filters, cutoff, engine, and optional semantic provider/model recorded?

## Coverage and relevance

- Does the governed corpus plausibly contain the evidence needed for the decision?
- Were vocabulary mismatch, exact identifiers, versions, exceptions, and counter-sources considered?
- Do top results bear on the real question rather than sharing attractive words?
- Did duplicates or one prolific source crowd out necessary diversity?

## Context and trust

- Does the context fit its declared budget without severing citations?
- Are retrieved passages clearly separated from model instructions?
- Did document-borne instructions, scripts, or claims remain untrusted evidence?
- Are sensitive paths or content exposed beyond the authorized audience?

## Answer support

- Can each consequential answer claim be traced to the cited passage?
- Does the citation resolve to the exact source and lines quoted?
- Are contradictions, staleness, missing authority, and source quality visible?
- Does the answer distinguish what was retrieved from what was inferred?

## Evaluation

- Were cases derived from real information needs rather than the current ranker?
- Are relevant-source labels defensible and independent of result order?
- Are recall, reciprocal rank, citation validity, and budget adherence calculated from raw results?
- Does an indispensable miss override an attractive average?

## Disposition

A package is `ready` only for the named corpus, engine, queries, and evidence burden. Use `ready-with-bounds` for explicit unexecuted evidence classes that do not conceal a material retrieval defect. Use `revise` when a repair is available, `insufficient-evidence` when the required proof is absent, and `blocked-by-environment` when the environment prevented the relevant observation.
