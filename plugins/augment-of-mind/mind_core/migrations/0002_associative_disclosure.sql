BEGIN IMMEDIATE;

ALTER TABLE capabilities
ADD COLUMN exposure_policy TEXT NOT NULL DEFAULT 'public_safe'
CHECK (exposure_policy IN ('public_safe', 'agent_private'));

ALTER TABLE capabilities
ADD COLUMN owner_agent_instance_id TEXT REFERENCES agent_instances(agent_instance_id);

CREATE INDEX capabilities_visibility_idx
ON capabilities(exposure_policy, owner_agent_instance_id, handle);

CREATE TRIGGER capabilities_visibility_insert_guard
BEFORE INSERT ON capabilities
BEGIN
  SELECT RAISE(ABORT, 'capability visibility binding is invalid')
  WHERE NOT (
    (NEW.exposure_policy = 'public_safe' AND NEW.owner_agent_instance_id IS NULL)
    OR
    (NEW.exposure_policy = 'agent_private' AND NEW.owner_agent_instance_id IS NOT NULL)
  );
END;

CREATE TRIGGER capabilities_visibility_update_guard
BEFORE UPDATE OF exposure_policy, owner_agent_instance_id ON capabilities
BEGIN
  SELECT RAISE(ABORT, 'capability visibility binding is invalid')
  WHERE NOT (
    (NEW.exposure_policy = 'public_safe' AND NEW.owner_agent_instance_id IS NULL)
    OR
    (NEW.exposure_policy = 'agent_private' AND NEW.owner_agent_instance_id IS NOT NULL)
  );
END;

CREATE TRIGGER capabilities_active_snapshot_visibility_guard
BEFORE UPDATE OF handle, exposure_policy, owner_agent_instance_id ON capabilities
BEGIN
  SELECT RAISE(ABORT, 'activated capability visibility is immutable')
  WHERE EXISTS (
    SELECT 1
    FROM capability_cards AS card
    JOIN associative_snapshot_cards AS membership
      ON membership.capability_card_id = card.capability_card_id
    JOIN associative_snapshot_activations AS activation
      ON activation.associative_index_snapshot_id = membership.associative_index_snapshot_id
    WHERE card.capability_id = OLD.capability_id
  );
END;

CREATE TRIGGER capability_aliases_active_snapshot_insert_guard
BEFORE INSERT ON capability_aliases
BEGIN
  SELECT RAISE(ABORT, 'activated capability aliases are immutable')
  WHERE EXISTS (
    SELECT 1
    FROM capability_cards AS card
    JOIN associative_snapshot_cards AS membership
      ON membership.capability_card_id = card.capability_card_id
    JOIN associative_snapshot_activations AS activation
      ON activation.associative_index_snapshot_id = membership.associative_index_snapshot_id
    WHERE card.capability_id = NEW.capability_id
  );
END;

CREATE TRIGGER capability_aliases_active_snapshot_update_guard
BEFORE UPDATE ON capability_aliases
BEGIN
  SELECT RAISE(ABORT, 'activated capability aliases are immutable')
  WHERE EXISTS (
    SELECT 1
    FROM capability_cards AS card
    JOIN associative_snapshot_cards AS membership
      ON membership.capability_card_id = card.capability_card_id
    JOIN associative_snapshot_activations AS activation
      ON activation.associative_index_snapshot_id = membership.associative_index_snapshot_id
    WHERE card.capability_id IN (OLD.capability_id, NEW.capability_id)
  );
END;

CREATE TRIGGER capability_aliases_active_snapshot_delete_guard
BEFORE DELETE ON capability_aliases
BEGIN
  SELECT RAISE(ABORT, 'activated capability aliases are immutable')
  WHERE EXISTS (
    SELECT 1
    FROM capability_cards AS card
    JOIN associative_snapshot_cards AS membership
      ON membership.capability_card_id = card.capability_card_id
    JOIN associative_snapshot_activations AS activation
      ON activation.associative_index_snapshot_id = membership.associative_index_snapshot_id
    WHERE card.capability_id = OLD.capability_id
  );
END;

CREATE TABLE associative_clusters (
    cluster_id TEXT PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_digest TEXT NOT NULL CHECK (length(source_digest) > 0),
    cluster_digest TEXT NOT NULL CHECK (length(cluster_digest) > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
) STRICT;

CREATE TABLE capability_cards (
    capability_card_id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    compact_projection TEXT NOT NULL,
    boundaries TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    exposure_policy TEXT NOT NULL CHECK (exposure_policy IN ('public_safe', 'agent_private')),
    owner_agent_instance_id TEXT,
    source_id TEXT NOT NULL,
    source_digest TEXT NOT NULL CHECK (length(source_digest) > 0),
    card_digest TEXT NOT NULL CHECK (length(card_digest) > 0),
    context_cost INTEGER NOT NULL CHECK (context_cost >= 0),
    created_at TEXT NOT NULL,
    UNIQUE (capability_id, revision),
    CHECK (
        (exposure_policy = 'public_safe' AND owner_agent_instance_id IS NULL)
        OR
        (exposure_policy = 'agent_private' AND owner_agent_instance_id IS NOT NULL)
    ),
    FOREIGN KEY (capability_id) REFERENCES capabilities(capability_id),
    FOREIGN KEY (cluster_id) REFERENCES associative_clusters(cluster_id),
    FOREIGN KEY (owner_agent_instance_id) REFERENCES agent_instances(agent_instance_id),
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
) STRICT;

CREATE INDEX capability_cards_capability_revision_idx
ON capability_cards(capability_id, revision DESC);

CREATE INDEX capability_cards_visibility_idx
ON capability_cards(exposure_policy, owner_agent_instance_id, cluster_id);

CREATE TABLE capability_card_views (
    capability_card_view_id TEXT PRIMARY KEY,
    capability_card_id TEXT NOT NULL,
    view_kind TEXT NOT NULL CHECK (view_kind IN (
        'transformation',
        'situation',
        'positive_cue',
        'error_or_correction',
        'negative_boundary',
        'example'
    )),
    content TEXT NOT NULL,
    content_digest TEXT NOT NULL CHECK (length(content_digest) > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (capability_card_id) REFERENCES capability_cards(capability_card_id)
) STRICT;

CREATE INDEX capability_card_views_card_idx
ON capability_card_views(capability_card_id, view_kind);

CREATE TABLE capability_relations (
    capability_relation_id TEXT PRIMARY KEY,
    from_capability_card_id TEXT NOT NULL,
    to_capability_card_id TEXT NOT NULL,
    relation_kind TEXT NOT NULL CHECK (relation_kind IN (
        'bridges_to',
        'complements',
        'requires',
        'false_friend_of'
    )),
    source_id TEXT NOT NULL,
    source_digest TEXT NOT NULL CHECK (length(source_digest) > 0),
    relation_digest TEXT NOT NULL CHECK (length(relation_digest) > 0),
    created_at TEXT NOT NULL,
    CHECK (from_capability_card_id <> to_capability_card_id),
    UNIQUE (from_capability_card_id, to_capability_card_id, relation_kind, relation_digest),
    FOREIGN KEY (from_capability_card_id) REFERENCES capability_cards(capability_card_id),
    FOREIGN KEY (to_capability_card_id) REFERENCES capability_cards(capability_card_id),
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
) STRICT;

CREATE INDEX capability_relations_from_idx
ON capability_relations(from_capability_card_id, relation_kind, to_capability_card_id);

CREATE INDEX capability_relations_to_idx
ON capability_relations(to_capability_card_id, relation_kind, from_capability_card_id);

CREATE TABLE lexical_profiles (
    lexical_profile_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    normalization_contract TEXT NOT NULL
      CHECK (normalization_contract = 'nfkc-casefold-contiguous-token-v1'),
    unicode_token_grammar TEXT NOT NULL,
    cue_membership_contract TEXT NOT NULL,
    profile_digest TEXT NOT NULL CHECK (length(profile_digest) > 0),
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE embedding_profiles (
    embedding_profile_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    provider_id TEXT,
    model_id TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0 AND dimensions <= 4096),
    metric TEXT NOT NULL CHECK (metric = 'cosine_distance'),
    radius REAL NOT NULL CHECK (radius >= 0.0 AND radius <= 2.0),
    comparison_tolerance REAL NOT NULL CHECK (
      comparison_tolerance >= 0.0 AND comparison_tolerance <= 0.001
    ),
    vector_encoding TEXT NOT NULL CHECK (vector_encoding = 'float32_le'),
    qualification_state TEXT NOT NULL CHECK (qualification_state IN (
      'unqualified', 'test_only', 'behavior_qualified', 'fresh_host_qualified'
    )),
    qualification_evidence_ref TEXT NOT NULL,
    qualification_digest TEXT NOT NULL CHECK (length(qualification_digest) > 0),
    profile_digest TEXT NOT NULL CHECK (length(profile_digest) > 0),
    created_at TEXT NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
) STRICT;

CREATE TABLE associative_index_snapshots (
    associative_index_snapshot_id TEXT PRIMARY KEY,
    embedding_profile_id TEXT NOT NULL,
    lexical_profile_id TEXT NOT NULL,
    vector_coverage_state TEXT NOT NULL CHECK (
      vector_coverage_state IN ('complete', 'unavailable')
    ),
    estate_digest TEXT NOT NULL CHECK (length(estate_digest) > 0),
    source_digest TEXT NOT NULL CHECK (length(source_digest) > 0),
    card_digest TEXT NOT NULL CHECK (length(card_digest) > 0),
    profile_digest TEXT NOT NULL CHECK (length(profile_digest) > 0),
    snapshot_digest TEXT NOT NULL UNIQUE CHECK (length(snapshot_digest) > 0),
    builder_identity TEXT NOT NULL,
    evidence_boundary TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (embedding_profile_id) REFERENCES embedding_profiles(embedding_profile_id),
    FOREIGN KEY (lexical_profile_id) REFERENCES lexical_profiles(lexical_profile_id)
) STRICT;

CREATE INDEX associative_index_snapshots_profile_idx
ON associative_index_snapshots(embedding_profile_id, lexical_profile_id, created_at DESC);

CREATE TABLE associative_snapshot_cards (
    associative_index_snapshot_id TEXT NOT NULL,
    capability_card_id TEXT NOT NULL,
    source_digest TEXT NOT NULL CHECK (length(source_digest) > 0),
    card_digest TEXT NOT NULL CHECK (length(card_digest) > 0),
    PRIMARY KEY (associative_index_snapshot_id, capability_card_id),
    FOREIGN KEY (associative_index_snapshot_id)
      REFERENCES associative_index_snapshots(associative_index_snapshot_id),
    FOREIGN KEY (capability_card_id) REFERENCES capability_cards(capability_card_id)
) STRICT;

CREATE INDEX associative_snapshot_cards_card_idx
ON associative_snapshot_cards(capability_card_id, associative_index_snapshot_id);

CREATE TABLE associative_snapshot_relations (
    associative_index_snapshot_id TEXT NOT NULL,
    capability_relation_id TEXT NOT NULL,
    relation_digest TEXT NOT NULL CHECK (length(relation_digest) > 0),
    PRIMARY KEY (associative_index_snapshot_id, capability_relation_id),
    FOREIGN KEY (associative_index_snapshot_id)
      REFERENCES associative_index_snapshots(associative_index_snapshot_id),
    FOREIGN KEY (capability_relation_id) REFERENCES capability_relations(capability_relation_id)
) STRICT;

CREATE INDEX associative_snapshot_relations_relation_idx
ON associative_snapshot_relations(capability_relation_id, associative_index_snapshot_id);

CREATE TABLE associative_view_vectors (
    associative_index_snapshot_id TEXT NOT NULL,
    capability_card_view_id TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    vector_float32_le BLOB NOT NULL,
    vector_digest TEXT NOT NULL CHECK (length(vector_digest) > 0),
    PRIMARY KEY (associative_index_snapshot_id, capability_card_view_id),
    CHECK (length(vector_float32_le) = dimensions * 4),
    FOREIGN KEY (associative_index_snapshot_id)
      REFERENCES associative_index_snapshots(associative_index_snapshot_id),
    FOREIGN KEY (capability_card_view_id) REFERENCES capability_card_views(capability_card_view_id)
) STRICT;

CREATE INDEX associative_view_vectors_view_idx
ON associative_view_vectors(capability_card_view_id, associative_index_snapshot_id);

CREATE TABLE associative_snapshot_activations (
    associative_snapshot_activation_id TEXT PRIMARY KEY,
    associative_index_snapshot_id TEXT NOT NULL,
    prior_associative_index_snapshot_id TEXT,
    activated_at TEXT NOT NULL,
    activation_receipt_id TEXT NOT NULL,
    UNIQUE (associative_index_snapshot_id),
    CHECK (
        prior_associative_index_snapshot_id IS NULL
        OR prior_associative_index_snapshot_id <> associative_index_snapshot_id
    ),
    FOREIGN KEY (associative_index_snapshot_id)
      REFERENCES associative_index_snapshots(associative_index_snapshot_id),
    FOREIGN KEY (prior_associative_index_snapshot_id)
      REFERENCES associative_index_snapshots(associative_index_snapshot_id),
    FOREIGN KEY (activation_receipt_id) REFERENCES receipts(receipt_id)
) STRICT;

CREATE INDEX associative_snapshot_activations_current_idx
ON associative_snapshot_activations(activated_at DESC, associative_index_snapshot_id);

CREATE TABLE session_query_capabilities (
    token_hash TEXT PRIMARY KEY CHECK (
        length(token_hash) = 64
        AND token_hash NOT GLOB '*[^0-9a-f]*'
    ),
    agent_instance_id TEXT NOT NULL,
    host_session_id TEXT NOT NULL,
    session_epoch INTEGER NOT NULL CHECK (session_epoch >= 0),
    exposure_scope TEXT NOT NULL CHECK (
      exposure_scope IN ('public_only', 'public_and_agent_private')
    ),
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    issuance_receipt_id TEXT NOT NULL,
    CHECK (expires_at > issued_at),
    FOREIGN KEY (host_session_id, agent_instance_id)
      REFERENCES host_sessions(host_session_id, agent_instance_id),
    FOREIGN KEY (issuance_receipt_id) REFERENCES receipts(receipt_id)
) STRICT;

CREATE INDEX session_query_capabilities_scope_idx
ON session_query_capabilities(agent_instance_id, host_session_id, session_epoch, exposure_scope, expires_at);

CREATE TABLE session_capability_revocations (
    session_capability_revocation_id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL,
    revoked_at TEXT NOT NULL,
    revocation_receipt_id TEXT NOT NULL,
    UNIQUE (token_hash),
    FOREIGN KEY (token_hash) REFERENCES session_query_capabilities(token_hash),
    FOREIGN KEY (revocation_receipt_id) REFERENCES receipts(receipt_id)
) STRICT;

CREATE INDEX session_capability_revocations_token_idx
ON session_capability_revocations(token_hash, revoked_at DESC);

CREATE VIRTUAL TABLE capability_card_fts USING fts5(
    associative_index_snapshot_id UNINDEXED,
    capability_card_view_id UNINDEXED,
    capability_id UNINDEXED,
    handle,
    content
);

CREATE TRIGGER associative_view_vectors_snapshot_card_guard
BEFORE INSERT ON associative_view_vectors
BEGIN
  SELECT RAISE(ABORT, 'vector view card is absent from snapshot')
  WHERE NOT EXISTS (
    SELECT 1
    FROM capability_card_views AS view
    JOIN associative_snapshot_cards AS membership
      ON membership.capability_card_id = view.capability_card_id
    WHERE view.capability_card_view_id = NEW.capability_card_view_id
      AND membership.associative_index_snapshot_id = NEW.associative_index_snapshot_id
  );

  SELECT RAISE(ABORT, 'vector dimensions do not match embedding profile')
  WHERE NOT EXISTS (
    SELECT 1
    FROM associative_index_snapshots AS snapshot
    JOIN embedding_profiles AS profile
      ON profile.embedding_profile_id = snapshot.embedding_profile_id
    WHERE snapshot.associative_index_snapshot_id = NEW.associative_index_snapshot_id
      AND profile.dimensions = NEW.dimensions
  );
END;

CREATE TRIGGER associative_snapshot_cards_activated_guard
BEFORE INSERT ON associative_snapshot_cards
BEGIN
  SELECT RAISE(ABORT, 'activated snapshot membership is immutable')
  WHERE EXISTS (
    SELECT 1 FROM associative_snapshot_activations
    WHERE associative_index_snapshot_id = NEW.associative_index_snapshot_id
  );
END;

CREATE TRIGGER capability_card_views_activated_guard
BEFORE INSERT ON capability_card_views
BEGIN
  SELECT RAISE(ABORT, 'activated card views are immutable')
  WHERE EXISTS (
    SELECT 1
    FROM associative_snapshot_cards AS membership
    JOIN associative_snapshot_activations AS activation
      ON activation.associative_index_snapshot_id = membership.associative_index_snapshot_id
    WHERE membership.capability_card_id = NEW.capability_card_id
  );
END;

CREATE TRIGGER associative_snapshot_relations_activated_guard
BEFORE INSERT ON associative_snapshot_relations
BEGIN
  SELECT RAISE(ABORT, 'activated snapshot relations are immutable')
  WHERE EXISTS (
    SELECT 1 FROM associative_snapshot_activations
    WHERE associative_index_snapshot_id = NEW.associative_index_snapshot_id
  );
END;

CREATE TRIGGER associative_view_vectors_activated_guard
BEFORE INSERT ON associative_view_vectors
BEGIN
  SELECT RAISE(ABORT, 'activated snapshot vectors are immutable')
  WHERE EXISTS (
    SELECT 1 FROM associative_snapshot_activations
    WHERE associative_index_snapshot_id = NEW.associative_index_snapshot_id
  );
END;

CREATE TRIGGER associative_snapshot_relations_membership_guard
BEFORE INSERT ON associative_snapshot_relations
BEGIN
  SELECT RAISE(ABORT, 'relation endpoint is absent from snapshot')
  WHERE NOT EXISTS (
    SELECT 1
    FROM capability_relations AS relation
    JOIN associative_snapshot_cards AS from_membership
      ON from_membership.capability_card_id = relation.from_capability_card_id
    JOIN associative_snapshot_cards AS to_membership
      ON to_membership.capability_card_id = relation.to_capability_card_id
    WHERE relation.capability_relation_id = NEW.capability_relation_id
      AND from_membership.associative_index_snapshot_id = NEW.associative_index_snapshot_id
      AND to_membership.associative_index_snapshot_id = NEW.associative_index_snapshot_id
  );
END;

CREATE TRIGGER session_query_capabilities_epoch_guard
BEFORE INSERT ON session_query_capabilities
BEGIN
  SELECT RAISE(ABORT, 'session capability epoch is incompatible')
  WHERE NOT EXISTS (
    SELECT 1
    FROM host_sessions
    WHERE host_session_id = NEW.host_session_id
      AND agent_instance_id = NEW.agent_instance_id
      AND session_epoch = NEW.session_epoch
  );
END;

CREATE TRIGGER associative_clusters_no_update
BEFORE UPDATE ON associative_clusters
BEGIN
  SELECT RAISE(ABORT, 'associative clusters are immutable');
END;

CREATE TRIGGER associative_clusters_no_delete
BEFORE DELETE ON associative_clusters
BEGIN
  SELECT RAISE(ABORT, 'associative clusters are immutable');
END;

CREATE TRIGGER capability_cards_no_update
BEFORE UPDATE ON capability_cards
BEGIN
  SELECT RAISE(ABORT, 'capability cards are immutable');
END;

CREATE TRIGGER capability_cards_no_delete
BEFORE DELETE ON capability_cards
BEGIN
  SELECT RAISE(ABORT, 'capability cards are immutable');
END;

CREATE TRIGGER capability_card_views_no_update
BEFORE UPDATE ON capability_card_views
BEGIN
  SELECT RAISE(ABORT, 'capability card views are immutable');
END;

CREATE TRIGGER capability_card_views_no_delete
BEFORE DELETE ON capability_card_views
BEGIN
  SELECT RAISE(ABORT, 'capability card views are immutable');
END;

CREATE TRIGGER capability_relations_no_update
BEFORE UPDATE ON capability_relations
BEGIN
  SELECT RAISE(ABORT, 'capability relations are immutable');
END;

CREATE TRIGGER capability_relations_no_delete
BEFORE DELETE ON capability_relations
BEGIN
  SELECT RAISE(ABORT, 'capability relations are immutable');
END;

CREATE TRIGGER lexical_profiles_no_update
BEFORE UPDATE ON lexical_profiles
BEGIN
  SELECT RAISE(ABORT, 'lexical profiles are immutable');
END;

CREATE TRIGGER lexical_profiles_no_delete
BEFORE DELETE ON lexical_profiles
BEGIN
  SELECT RAISE(ABORT, 'lexical profiles are immutable');
END;

CREATE TRIGGER embedding_profiles_no_update
BEFORE UPDATE ON embedding_profiles
BEGIN
  SELECT RAISE(ABORT, 'embedding profiles are immutable');
END;

CREATE TRIGGER embedding_profiles_no_delete
BEFORE DELETE ON embedding_profiles
BEGIN
  SELECT RAISE(ABORT, 'embedding profiles are immutable');
END;

CREATE TRIGGER associative_index_snapshots_no_update
BEFORE UPDATE ON associative_index_snapshots
BEGIN
  SELECT RAISE(ABORT, 'associative index snapshots are immutable');
END;

CREATE TRIGGER associative_index_snapshots_no_delete
BEFORE DELETE ON associative_index_snapshots
BEGIN
  SELECT RAISE(ABORT, 'associative index snapshots are immutable');
END;

CREATE TRIGGER associative_snapshot_cards_no_update
BEFORE UPDATE ON associative_snapshot_cards
BEGIN
  SELECT RAISE(ABORT, 'snapshot card membership is immutable');
END;

CREATE TRIGGER associative_snapshot_cards_no_delete
BEFORE DELETE ON associative_snapshot_cards
BEGIN
  SELECT RAISE(ABORT, 'snapshot card membership is immutable');
END;

CREATE TRIGGER associative_snapshot_relations_no_update
BEFORE UPDATE ON associative_snapshot_relations
BEGIN
  SELECT RAISE(ABORT, 'snapshot relation membership is immutable');
END;

CREATE TRIGGER associative_snapshot_relations_no_delete
BEFORE DELETE ON associative_snapshot_relations
BEGIN
  SELECT RAISE(ABORT, 'snapshot relation membership is immutable');
END;

CREATE TRIGGER associative_view_vectors_no_update
BEFORE UPDATE ON associative_view_vectors
BEGIN
  SELECT RAISE(ABORT, 'associative view vectors are immutable');
END;

CREATE TRIGGER associative_view_vectors_no_delete
BEFORE DELETE ON associative_view_vectors
BEGIN
  SELECT RAISE(ABORT, 'associative view vectors are immutable');
END;

CREATE TRIGGER associative_snapshot_activations_no_update
BEFORE UPDATE ON associative_snapshot_activations
BEGIN
  SELECT RAISE(ABORT, 'snapshot activations are append-only');
END;

CREATE TRIGGER associative_snapshot_activations_no_delete
BEFORE DELETE ON associative_snapshot_activations
BEGIN
  SELECT RAISE(ABORT, 'snapshot activations are append-only');
END;

CREATE TRIGGER session_query_capabilities_no_update
BEFORE UPDATE ON session_query_capabilities
BEGIN
  SELECT RAISE(ABORT, 'session query capabilities are immutable');
END;

CREATE TRIGGER session_query_capabilities_no_delete
BEFORE DELETE ON session_query_capabilities
BEGIN
  SELECT RAISE(ABORT, 'session query capabilities are immutable');
END;

CREATE TRIGGER session_capability_revocations_no_update
BEFORE UPDATE ON session_capability_revocations
BEGIN
  SELECT RAISE(ABORT, 'session capability revocations are append-only');
END;

CREATE TRIGGER session_capability_revocations_no_delete
BEFORE DELETE ON session_capability_revocations
BEGIN
  SELECT RAISE(ABORT, 'session capability revocations are append-only');
END;

UPDATE core_meta
SET value = '2', updated_at = '{{APPLIED_AT}}'
WHERE key = 'schema_version';

UPDATE core_meta
SET value = 'mind-core/0.2', updated_at = '{{APPLIED_AT}}'
WHERE key = 'protocol_version';

INSERT INTO schema_migrations(migration_id, checksum, applied_at, runner_version)
VALUES ('0002_associative_disclosure', '{{CHECKSUM}}', '{{APPLIED_AT}}', '{{RUNNER_VERSION}}');

PRAGMA user_version = 2;

COMMIT;
