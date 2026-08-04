BEGIN IMMEDIATE;

CREATE TABLE schema_migrations (
    migration_id TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    runner_version TEXT NOT NULL
) STRICT;

CREATE TABLE core_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
) STRICT;

CREATE TABLE agent_instances (
    agent_instance_id TEXT PRIMARY KEY,
    persona_id TEXT,
    profile_id TEXT,
    created_at TEXT NOT NULL,
    retired_at TEXT,
    CHECK (retired_at IS NULL OR retired_at >= created_at)
) STRICT;

CREATE TABLE host_sessions (
    host_session_id TEXT PRIMARY KEY,
    host_id TEXT NOT NULL,
    external_session_id TEXT NOT NULL,
    session_epoch INTEGER NOT NULL CHECK (session_epoch >= 0),
    agent_instance_id TEXT NOT NULL,
    adapter_id TEXT NOT NULL,
    adapter_version TEXT NOT NULL,
    protocol_version TEXT NOT NULL,
    declared_conformance_level TEXT NOT NULL CHECK (declared_conformance_level IN ('H0','H1','H2','H3')),
    evidence_conformance_level TEXT NOT NULL CHECK (evidence_conformance_level = 'H0'),
    catalog_snapshot_hash TEXT NOT NULL,
    catalog_snapshot_expires_at TEXT NOT NULL,
    permission_observation_hash TEXT NOT NULL,
    authentication_observation_hash TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    CHECK (expires_at > observed_at),
    CHECK (catalog_snapshot_expires_at > observed_at),
    UNIQUE (host_id, external_session_id, session_epoch, agent_instance_id),
    UNIQUE (host_session_id, agent_instance_id),
    FOREIGN KEY (agent_instance_id) REFERENCES agent_instances(agent_instance_id)
) STRICT;

CREATE INDEX host_sessions_scope_idx
ON host_sessions(agent_instance_id, host_session_id, expires_at);

CREATE TABLE event_coverage (
    coverage_id TEXT PRIMARY KEY,
    host_session_id TEXT NOT NULL,
    agent_instance_id TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    action_class TEXT NOT NULL DEFAULT '',
    source_observer TEXT NOT NULL,
    timing TEXT NOT NULL CHECK (timing IN ('pre_action','post_action','next_turn','unobservable')),
    delivery_durability TEXT NOT NULL,
    correlation_method TEXT NOT NULL,
    declared_coverage_state TEXT NOT NULL CHECK (declared_coverage_state IN ('enforced','cooperative','advisory_only','unobservable')),
    effective_coverage_state TEXT NOT NULL CHECK (effective_coverage_state IN ('advisory_only','unobservable')),
    evidence_conformance_level TEXT NOT NULL CHECK (evidence_conformance_level = 'H0'),
    observed_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    source_receipt_ref TEXT,
    CHECK (expires_at > observed_at),
    FOREIGN KEY (host_session_id, agent_instance_id)
      REFERENCES host_sessions(host_session_id, agent_instance_id)
) STRICT;

CREATE INDEX event_coverage_scope_idx
ON event_coverage(agent_instance_id, host_session_id, event_kind, action_class, observed_at DESC);

CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    locator TEXT NOT NULL,
    digest TEXT,
    custody_state TEXT NOT NULL,
    authority_ref TEXT NOT NULL,
    observed_at TEXT NOT NULL
) STRICT;

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    canonical_uri TEXT,
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE providers (
    provider_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    provider_kind TEXT NOT NULL,
    canonical_uri TEXT,
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE capabilities (
    capability_id TEXT PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    product_id TEXT,
    canonical_source_id TEXT,
    promise TEXT NOT NULL,
    negative_space TEXT NOT NULL,
    created_at TEXT NOT NULL,
    superseded_by TEXT,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (canonical_source_id) REFERENCES sources(source_id),
    FOREIGN KEY (superseded_by) REFERENCES capabilities(capability_id)
) STRICT;

CREATE TABLE capability_aliases (
    capability_id TEXT NOT NULL,
    namespace TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    display_alias TEXT NOT NULL,
    PRIMARY KEY (capability_id, namespace, normalized_alias),
    FOREIGN KEY (capability_id) REFERENCES capabilities(capability_id)
) STRICT;

CREATE INDEX capability_alias_lookup_idx
ON capability_aliases(namespace, normalized_alias);

CREATE TABLE capability_entrypoints (
    capability_id TEXT NOT NULL,
    entrypoint_id TEXT NOT NULL,
    entrypoint_kind TEXT NOT NULL,
    locator TEXT NOT NULL,
    operation TEXT NOT NULL,
    PRIMARY KEY (capability_id, entrypoint_id),
    FOREIGN KEY (capability_id) REFERENCES capabilities(capability_id)
) STRICT;

CREATE TABLE distributions (
    distribution_id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL,
    product_id TEXT,
    provider_id TEXT NOT NULL,
    version TEXT NOT NULL,
    package_form TEXT NOT NULL,
    artifact_digest TEXT,
    source_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (distribution_id, capability_id),
    FOREIGN KEY (capability_id) REFERENCES capabilities(capability_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (provider_id) REFERENCES providers(provider_id),
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
) STRICT;

CREATE INDEX distributions_capability_idx
ON distributions(capability_id, provider_id, version);

CREATE TABLE lifecycle_state_defs (
    axis TEXT NOT NULL,
    state TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    PRIMARY KEY (axis, state)
) STRICT;

CREATE TABLE lifecycle_observations (
    observation_id TEXT PRIMARY KEY,
    capability_id TEXT NOT NULL,
    distribution_id TEXT,
    axis TEXT NOT NULL,
    state TEXT NOT NULL,
    agent_instance_id TEXT,
    host_session_id TEXT,
    observed_at TEXT NOT NULL,
    expires_at TEXT,
    evidence_receipt_id TEXT NOT NULL,
    source_reference TEXT NOT NULL,
    CHECK (
      (axis IN ('custody','distribution','governance')
       AND agent_instance_id IS NULL AND host_session_id IS NULL)
      OR
      (axis IN ('host_presence','runtime_use','fitness')
       AND agent_instance_id IS NOT NULL AND host_session_id IS NOT NULL)
    ),
    CHECK (expires_at IS NULL OR expires_at > observed_at),
    FOREIGN KEY (axis, state) REFERENCES lifecycle_state_defs(axis, state),
    FOREIGN KEY (capability_id) REFERENCES capabilities(capability_id),
    FOREIGN KEY (distribution_id, capability_id)
      REFERENCES distributions(distribution_id, capability_id),
    FOREIGN KEY (host_session_id, agent_instance_id)
      REFERENCES host_sessions(host_session_id, agent_instance_id),
    FOREIGN KEY (evidence_receipt_id) REFERENCES receipts(receipt_id)
) STRICT;

CREATE INDEX lifecycle_observations_capability_idx
ON lifecycle_observations(capability_id, distribution_id, axis, observed_at DESC);

CREATE INDEX lifecycle_observations_scope_idx
ON lifecycle_observations(agent_instance_id, host_session_id, observed_at DESC);

CREATE TABLE mounts (
    mount_id TEXT PRIMARY KEY,
    handle TEXT NOT NULL UNIQUE,
    owner_id TEXT NOT NULL,
    mount_class TEXT NOT NULL,
    purpose TEXT NOT NULL,
    front_door TEXT NOT NULL,
    registration_state TEXT NOT NULL CHECK (registration_state IN ('registered','known_unregistered')),
    registration_provenance TEXT NOT NULL,
    canonical_role TEXT NOT NULL CHECK (canonical_role IN ('canonical','derived','catalog_only')),
    sensitivity_ceiling TEXT NOT NULL,
    portability TEXT NOT NULL,
    indexing_eligibility TEXT NOT NULL,
    export_eligibility TEXT NOT NULL,
    created_at TEXT NOT NULL
) STRICT;

CREATE TABLE mount_grants (
    grant_id TEXT PRIMARY KEY,
    mount_id TEXT NOT NULL,
    agent_instance_id TEXT NOT NULL,
    host_session_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    sensitivity_ceiling TEXT NOT NULL,
    allowed_operations_json TEXT NOT NULL,
    authority_ref TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    evidence_receipt_id TEXT NOT NULL,
    CHECK (expires_at > observed_at),
    FOREIGN KEY (mount_id) REFERENCES mounts(mount_id),
    FOREIGN KEY (host_session_id, agent_instance_id)
      REFERENCES host_sessions(host_session_id, agent_instance_id),
    FOREIGN KEY (evidence_receipt_id) REFERENCES receipts(receipt_id)
) STRICT;

CREATE INDEX mount_grants_scope_idx
ON mount_grants(agent_instance_id, host_session_id, mount_id, expires_at);

CREATE TABLE mount_observations (
    mount_observation_id TEXT PRIMARY KEY,
    mount_id TEXT NOT NULL,
    agent_instance_id TEXT NOT NULL,
    host_session_id TEXT NOT NULL,
    availability_state TEXT NOT NULL CHECK (availability_state IN (
      'READY_CURRENT','READ_ONLY_CURRENT','STALE_SNAPSHOT','MOUNT_ABSENT',
      'BACKEND_UNAVAILABLE','DENIED_SCOPE','INTEGRITY_FAILED','PARTIAL',
      'AUTHORITATIVE_EMPTY','BROKER_UNAVAILABLE'
    )),
    path_visible INTEGER CHECK (path_visible IN (0,1) OR path_visible IS NULL),
    runtime_openable INTEGER CHECK (runtime_openable IN (0,1) OR runtime_openable IS NULL),
    schema_valid INTEGER CHECK (schema_valid IN (0,1) OR schema_valid IS NULL),
    integrity_valid INTEGER CHECK (integrity_valid IN (0,1) OR integrity_valid IS NULL),
    authoritative_read_succeeded INTEGER CHECK (
      authoritative_read_succeeded IN (0,1) OR authoritative_read_succeeded IS NULL
    ),
    failure_boundary TEXT,
    observed_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    evidence_receipt_id TEXT NOT NULL,
    CHECK (expires_at > observed_at),
    FOREIGN KEY (mount_id) REFERENCES mounts(mount_id),
    FOREIGN KEY (host_session_id, agent_instance_id)
      REFERENCES host_sessions(host_session_id, agent_instance_id),
    FOREIGN KEY (evidence_receipt_id) REFERENCES receipts(receipt_id)
) STRICT;

CREATE INDEX mount_observations_scope_idx
ON mount_observations(agent_instance_id, host_session_id, mount_id, observed_at DESC);

CREATE TABLE receipts (
    receipt_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL,
    receipt_type TEXT NOT NULL,
    subject_kind TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    agent_instance_id TEXT,
    host_session_id TEXT,
    evidence_state TEXT NOT NULL CHECK (evidence_state IN (
      'reported','attempted','tool_returned','observed','reconciled',
      'independently_verified','inferred','unavailable'
    )),
    claimed_boundary TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    expires_at TEXT,
    redaction_class TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    content_digest TEXT NOT NULL,
    CHECK (
      (agent_instance_id IS NULL AND host_session_id IS NULL)
      OR (agent_instance_id IS NOT NULL AND host_session_id IS NOT NULL)
    ),
    CHECK (expires_at IS NULL OR expires_at > observed_at),
    FOREIGN KEY (host_session_id, agent_instance_id)
      REFERENCES host_sessions(host_session_id, agent_instance_id)
) STRICT;

CREATE INDEX receipts_subject_idx
ON receipts(subject_kind, subject_id, recorded_at DESC);

CREATE INDEX receipts_scope_idx
ON receipts(agent_instance_id, host_session_id, recorded_at DESC);

CREATE UNIQUE INDEX receipts_global_idempotency_idx
ON receipts(idempotency_key)
WHERE agent_instance_id IS NULL AND host_session_id IS NULL;

CREATE UNIQUE INDEX receipts_scoped_idempotency_idx
ON receipts(agent_instance_id, host_session_id, idempotency_key)
WHERE agent_instance_id IS NOT NULL AND host_session_id IS NOT NULL;

CREATE TABLE receipt_edges (
    child_receipt_id TEXT NOT NULL,
    parent_receipt_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    PRIMARY KEY (child_receipt_id, parent_receipt_id, relation),
    CHECK (child_receipt_id <> parent_receipt_id),
    FOREIGN KEY (child_receipt_id) REFERENCES receipts(receipt_id),
    FOREIGN KEY (parent_receipt_id) REFERENCES receipts(receipt_id)
) STRICT;

CREATE TRIGGER receipts_no_update
BEFORE UPDATE ON receipts
BEGIN
  SELECT RAISE(ABORT, 'receipts are append-only');
END;

CREATE TRIGGER receipts_no_delete
BEFORE DELETE ON receipts
BEGIN
  SELECT RAISE(ABORT, 'receipts are append-only');
END;

CREATE TRIGGER receipt_edges_no_update
BEFORE UPDATE ON receipt_edges
BEGIN
  SELECT RAISE(ABORT, 'receipt edges are append-only');
END;

CREATE TRIGGER receipt_edges_no_delete
BEFORE DELETE ON receipt_edges
BEGIN
  SELECT RAISE(ABORT, 'receipt edges are append-only');
END;

CREATE TRIGGER receipt_edges_scope_guard
BEFORE INSERT ON receipt_edges
BEGIN
  SELECT RAISE(ABORT, 'receipt parent scope is incompatible')
  WHERE EXISTS (
    SELECT 1
    FROM receipts AS child
    JOIN receipts AS parent
      ON parent.receipt_id = NEW.parent_receipt_id
    WHERE child.receipt_id = NEW.child_receipt_id
      AND (
        (child.agent_instance_id IS NULL AND parent.agent_instance_id IS NOT NULL)
        OR
        (child.agent_instance_id IS NOT NULL
         AND parent.agent_instance_id IS NOT NULL
         AND (
           child.agent_instance_id <> parent.agent_instance_id
           OR child.host_session_id <> parent.host_session_id
         ))
      )
  );
END;

CREATE TRIGGER receipt_edges_no_cycle
BEFORE INSERT ON receipt_edges
BEGIN
  SELECT RAISE(ABORT, 'receipt parent cycle is forbidden')
  WHERE EXISTS (
    WITH RECURSIVE ancestors(receipt_id) AS (
      SELECT parent_receipt_id
      FROM receipt_edges
      WHERE child_receipt_id = NEW.parent_receipt_id
      UNION
      SELECT edge.parent_receipt_id
      FROM receipt_edges AS edge
      JOIN ancestors ON edge.child_receipt_id = ancestors.receipt_id
    )
    SELECT 1 FROM ancestors WHERE receipt_id = NEW.child_receipt_id
  );
END;

CREATE TRIGGER lifecycle_observations_no_update
BEFORE UPDATE ON lifecycle_observations
BEGIN
  SELECT RAISE(ABORT, 'lifecycle observations are append-only');
END;

CREATE TRIGGER lifecycle_observations_no_delete
BEFORE DELETE ON lifecycle_observations
BEGIN
  SELECT RAISE(ABORT, 'lifecycle observations are append-only');
END;

CREATE TRIGGER event_coverage_no_update
BEFORE UPDATE ON event_coverage
BEGIN
  SELECT RAISE(ABORT, 'event coverage observations are append-only');
END;

CREATE TRIGGER event_coverage_no_delete
BEFORE DELETE ON event_coverage
BEGIN
  SELECT RAISE(ABORT, 'event coverage observations are append-only');
END;

CREATE TRIGGER mount_grants_no_update
BEFORE UPDATE ON mount_grants
BEGIN
  SELECT RAISE(ABORT, 'mount grants are append-only');
END;

CREATE TRIGGER mount_grants_no_delete
BEFORE DELETE ON mount_grants
BEGIN
  SELECT RAISE(ABORT, 'mount grants are append-only');
END;

CREATE TRIGGER mount_observations_no_update
BEFORE UPDATE ON mount_observations
BEGIN
  SELECT RAISE(ABORT, 'mount observations are append-only');
END;

CREATE TRIGGER mount_observations_no_delete
BEFORE DELETE ON mount_observations
BEGIN
  SELECT RAISE(ABORT, 'mount observations are append-only');
END;

INSERT INTO lifecycle_state_defs(axis, state, ordinal) VALUES
  ('custody','conceived',0),
  ('custody','source-located',1),
  ('custody','canonical-constructed',2),
  ('custody','superseded',3),
  ('custody','retired',4),
  ('distribution','not-generated',0),
  ('distribution','generated',1),
  ('distribution','structurally-verified',2),
  ('distribution','released',3),
  ('host_presence','not-observed',0),
  ('host_presence','installed',1),
  ('host_presence','discovered',2),
  ('host_presence','injected',3),
  ('runtime_use','selected',0),
  ('runtime_use','resources-loaded',1),
  ('runtime_use','operationally-bound',2),
  ('runtime_use','invoked',3),
  ('runtime_use','receipt-returned',4),
  ('fitness','untested',0),
  ('fitness','package-qualified',1),
  ('fitness','behavior-qualified',2),
  ('fitness','fresh-host-qualified',3),
  ('fitness','healthy',4),
  ('fitness','degraded',5),
  ('governance','candidate',0),
  ('governance','approved',1),
  ('governance','deprecated',2),
  ('governance','blocked',3);

INSERT INTO core_meta(key, value, updated_at) VALUES
  ('schema_version', '1', '{{APPLIED_AT}}'),
  ('protocol_version', 'mind-core/0.1', '{{APPLIED_AT}}'),
  ('maximum_host_conformance', 'H0', '{{APPLIED_AT}}'),
  ('persona_requirement', 'optional-never-inferred', '{{APPLIED_AT}}');

INSERT INTO schema_migrations(migration_id, checksum, applied_at, runner_version)
VALUES ('0001_core_metadata', '{{CHECKSUM}}', '{{APPLIED_AT}}', '{{RUNNER_VERSION}}');

PRAGMA application_id = 1296649796;
PRAGMA user_version = 1;

COMMIT;
