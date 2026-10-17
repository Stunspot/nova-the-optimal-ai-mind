# Semantic fusion contract

The local baseline performs lexical retrieval. Semantic fusion is optional and may enter only through an inspectable score artifact.

The score artifact is JSON with this shape:

```json
{
  "schema": "retrieval-semantic-scores-v1",
  "index_id": "sha256 identity reported by rag.py inspect",
  "provider": "local-or-service-name",
  "model": "exact model identifier",
  "query": "the exact query embedded",
  "scores": {
    "chunk-id": 0.91
  }
}
```

Scores must be finite numbers between 0 and 1. The index identity and query must match the active search. Record whether source text left the machine, what was retained by the provider, and who authorized that transfer. The engine fuses lexical and semantic rankings; it does not create embeddings.

Reject a score artifact with an unknown schema, mismatched query or index, missing provider/model identity, invalid scores, or chunk IDs absent from the index. A successful fusion proves only that the supplied rankings were combined as specified.
