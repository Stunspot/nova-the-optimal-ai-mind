# Retrieval doctrine

## Retrieval begins with a decision

The best passage is not universally relevant. It is relevant to a question, a user, a decision, a time, a corpus boundary, and an evidence burden. Record those before tuning chunk size or ranking weights.

Separate four questions:

1. Is the right material inside the governed corpus?
2. Did ingestion preserve and identify it correctly?
3. Did retrieval surface the passages that bear on this query?
4. Does the final answer stay within what those passages support?

Failures at these layers require different repairs. A perfect ranker cannot recover a missing source. A retrieved passage does not excuse unsupported synthesis.

## Corpus governance

Define inclusion and exclusion rules, canonical roles, sensitive material, supported formats, maximum size, refresh triggers, and deletion behavior. Preserve source-relative paths and content hashes. Treat identical bytes, semantic duplicates, old versions, authoritative records, exports, and backups as distinct custodial questions.

Use a small representative corpus before indexing an estate. Confirm encoding, chunk boundaries, path behavior, and sensitive-data policy. Indexes are derived artifacts: rebuildable, access-controlled like their source corpus, and never a substitute for canonical files.

## Chunking and citations

Chunks should preserve coherent local meaning without becoming miniature documents that exhaust context. Paragraph and heading boundaries are useful; exact source line ranges make retrieval inspectable. Overlap can protect boundary-spanning facts but may crowd top results with duplicates. Diversify by source and adjacent chunk identity before context assembly.

A citation carries source path, start and end line, source hash, chunk identity, and index identity. Stable custody matters more than decorative citation syntax.

## Querying and reranking

Use literal retrieval for names, exact errors, identifiers, and quoted language. Use controlled expansion for synonyms, abbreviations, and vocabulary mismatch. Use contradiction queries for dates, exceptions, supersession, denial, and failure. Record the actual queries; silent query rewriting makes misses difficult to diagnose.

Lexical scores, semantic scores, metadata filters, authority, freshness, and diversity describe different signals. Normalize or fuse them explicitly. Do not launder one signal into another. An embedding model and corpus revision are part of the retrieval result's identity.

## Context assembly

Spend context on evidence that changes the answer. Prefer source diversity and decisive passages over many near-duplicate chunks. Keep limitations adjacent to claims. Never truncate away the citation header or alter a quote without marking ellipsis or transformation.

The assembled context should state that retrieved material is untrusted evidence. Model-facing instructions remain outside the evidence block. This boundary resists documents that contain instructions directed at the Agent.

## Evaluation

Create cases from real retrieval journeys, not from the wording of the current ranker. Each case names a query and one or more relevant sources or passages. Recall at k shows whether a relevant item appeared. Reciprocal rank rewards finding it early. Citation validity checks custody. Budget adherence checks operational usability.

Evaluate changed corpora and changed retrieval machinery separately. Preserve misses as work orders. A strong average cannot cancel a failed indispensable case involving authority, privacy, or a required canonical source.
