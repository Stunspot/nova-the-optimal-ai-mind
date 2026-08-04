# AI-ENG-AC — AI Operations - Incident Response, Rollback & Runbook Design

## **Doctrinal Foundations: Semantic Incident Response vs. Uptime Operations**

Production reliability in high-dimensional artificial intelligence systems represents a fundamental break from traditional application performance monitoring (APM) and incident management paradigms.1 In legacy web architectures, system health is treated as a binary or scalar state defined by infrastructure metrics: a service is considered healthy when APIs return successful status codes, server workloads are balanced, database connections are active, and latency remains within acceptable thresholds.1 However, when these architectures are driven by probabilistic large language models (LLMs) and multi-agent loops, backend availability does not guarantee a successful, safe, or contextually coherent user transaction.1  
An artificial intelligence gateway can return a successful HTTP 200 payload that contains a complete structural schema failure, an unauthorized tool execution, a cross-tenant data leak, or an ungrounded factual confabulation.1 Conversely, a system can exhibit optimal hardware utilization and high throughput while delivering answers that silently violate safety boundaries, omit critical citations, or trap agentic loops in expensive, infinite executions.1 This mismatch establishes the Green Dashboard Fallacy: the diagnostic error of assuming an AI system is healthy based solely on infrastructure availability.1 In production AI engineering, a green infrastructure dashboard can easily coexist with a red behavioral and meaning-level system state.1  
This gap establishes the systems-engineering discipline of Semantic Incident Response.1 AI operations is defined as the incident-response and lifecycle discipline for systems that fail semantically, behaviorally, economically, procedurally, and socially—not merely infrastructurally.3 The core doctrine of this discipline dictates that AI incidents must be managed as behavioral and semantic failures, not merely service outages. Operational response must identify the failing layer, preserve evidence, contain harm, roll back the smallest effective component, communicate user impact, and convert the incident into durable evaluations, telemetry, policy, and runbook improvements.1  
The primary engineering inquiry moves from "Is the service online?" to "Is the system again producing safe, grounded, authorized, governed, cost-bounded, and user-appropriate behavior?".1 Managing this requires a clean distinction between service recovery and behavioral recovery.3 While service recovery focuses on transport availability, behavioral recovery restores the system's output to safe, grounded, and policy-compliant envelopes.3 Similarly, operators must distinguish mitigation—such as prompt modifications or cache flushes that bypass active symptoms—from permanent resolution via regression-verified code changes promoted through normal CI/CD gates.2  
This distinction is modeled mathematically as a Stackelberg game between the provider and the user to balance operational cost with user utility under degraded conditions.3 Let U_a represent the user utility derived from model action a, let t_a represent the latency delay associated with that action, and let c_a represent the monetary cost of the inference execution to the provider.3 The user's action selection seeks to maximize utility minus the latency penalty, moderated by a sensitivity parameter beta 3:  
max_{a in A} (U_a - beta * t_a)  
The provider, acting as the leader, optimizes its routing policies and interface disclosures to minimize operational service costs (sum of c_i) while maintaining user retention.3 If the interface fails to communicate degradation, the user's utility collapses as they over-rely on a downgraded system.3 Calibrating trust requires the system to dynamically expose its capabilities, limitations, and fallback states, transferring decision-making agency back to the user.3

## **Conceptual Glossary**

The following glossary defines the core operational metrics and terms governing high-dimensional AI operations and semantic incident response:

| Term | Technical Definition | Primary Operational Metric | Standard Production Target |
| :---- | :---- | :---- | :---- |
| **AI Incident** | A situation in which deployed intelligent systems cause, or very nearly cause, real-world harm, semantic degradation, policy violations, or unauthorized actions.4 | Systemic Incident Rate (R_inc) 2 | 0.00% of automated transaction pipelines 2 |
| **Semantic Failure** | An execution where the model output is syntactically valid but factually wrong, ungrounded, contextually irrelevant, or aligned with adversarial instructions.2 | Semantic Violation Rate (R_sem_violation) 2 | < 0.50% of evaluated transactions 2 |
| **Behavioral Recovery** | The operational restoration of a system's output to safe, grounded, and policy-compliant envelopes after a semantic failure, independent of service availability.3 | Mean Time to Behavioral Recovery (MTTBR) | < 5 minutes via automated circuit breakers 6 |
| **Prompt Hotfix** | An emergency, version-controlled override of a system prompt template or safety wrapper to address an active exploit or instruction failure.7 | Hotfix Verification Pass Rate | 100% compliance on automated regression gates 7 |
| **Model Rollback** | Reverting a serving route, adapter, or model checkpoint snapshot to a prior validated version when regressions or failures occur.8 | Revert Transition Latency | < 60 seconds at the gateway layer 8 |
| **Corpus Quarantine** | The physical or logical isolation of document batches, indexes, or vector database partitions suspected of containing poisoned or unauthorized data.2 | Quarantine Activation Delay | < 5 seconds from ingestion alert detection |
| **Retrieval Rollback** | Reverting a vector index, document routing policy, or chunking strategy to a prior verified state to neutralize RAG poisoning.2 | Index Reconstruction Time | < 15 minutes to re-establish clean HNSW graphs |
| **Kill Switch** | A hard, programmatic block managed outside the model's execution path to instantly disable specific agentic tools or capabilities.2 | Kill Switch Execution Latency | < 100 milliseconds via Edge proxy configurations 9 |
| **Feature Flag** | A dynamic, runtime configuration control used to selectively toggle models, prompts, routes, or agent capabilities for specific tenants or cohorts.3 | Flag Propagation Delay | < 500 milliseconds across global CDNs |
| **Blast Radius** | The maximum potential impact of an active failure, measured by affected tenants, transaction volumes, financial exposure, and safety risks.3 | Normalized Tenant Exposure Ratio | Scoped strictly to the failing tenant partition 2 |
| **Degraded-Mode Failure** | A condition where core platform components fail, forcing the system to step down to a restricted but safe quality band.3 | Active Degradation Exposure (D_exp) 3 | < 2.0% of rolling monthly sessions 3 |
| **Containment** | The rapid, temporary execution of blocks, overrides, or fallbacks to limit harm before the definitive root cause is identified.2 | Time to Containment (TTC) | < 2 minutes for critical security events 12 |
| **Mitigation** | Structural adjustments—such as prompt modifications or cache flushes—that bypass active symptoms while permanent code fixes are prepared.3 | Mitigation Success Rate | > 95% reduction in recurring incident triggers |
| **Resolution** | The permanent correction of the underlying system failure, verified by regression tests and promoted through normal CI/CD gates.2 | Regression Verification Coverage | 100% coverage of failure-trigger variants |
| **Incident-to-Eval Loop** | The automated pipeline that packages an incident trace, sanitizes sensitive data, and converts the failure into a permanent evaluation case.1 | Promotion Lead Time | < 24 hours from incident closure to CI/CD gate |

## **AI Incident Taxonomy**

Probabilistic failure modes are highly distributed and cross-cut multiple system layers.1 To facilitate rapid categorization and triage, the platform establishes a multi-dimensional AI Incident Taxonomy.4 Incidents are classified not by their infrastructure symptoms, but by their failing semantic layer and downstream consequences.2 A successful HTTP 200 response code can still be categorized as a critical SEV-1 failure if it delivered unauthorized, harmful, or ungrounded action guidance to the execution environment.1

```text
AI INCIDENT TAXONOMY MAP

[ External / User / Scheduled Input ]
        |
        v
+-------------------------------+
|  Intake and Boundary Layer    |
|  auth | tenant | policy | file |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Data and Evidence Layer      |
|  corpus | retrieval | cache   |
|  freshness | citation support |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Model and Reasoning Layer    |
|  semantic | grounding | prompt |
|  refusal | schema | drift     |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Agent and Action Layer       |
|  tool calls | workflows       |
|  idempotency | verification   |
+---------------+---------------+
                |
                v
+-------------------------------+
|  User / Governance Layer      |
|  disclosure | review | trust  |
|  compliance | communications  |
+---------------+---------------+
                |
                v
+-------------------------------+
|  Operations Response Layer    |
|  detect | contain | recover   |
|  notify | evaluate | prevent  |
+-------------------------------+

Incident classes are assigned by failing layer, consequence, active
propagation, reversibility, and evidence confidence. A green HTTP response
does not imply a healthy AI transaction.
```

The taxonomy maps sixteen distinct classes of system failure across the data ingestion, runtime processing, and interface delivery layers:

| Incident Class | Failing System Layer | Primary Diagnostic Indicator | Operational Symptom | Trace Correlation Attribute |
| :---- | :---- | :---- | :---- | :---- |
| **Semantic** | Cognitive / Inference 1 | nli_grounding_score < 0.70 1 | Confident output of false, ungrounded, or contradictory advice.1 | gen_ai.output.messages 1 |
| **Grounding** | Retrieval Context 1 | Delta_prior > 0.15 2 | Model answers from pre-trained weights, ignoring retrieved documents.2 | gen_ai.usage.input_tokens 1 |
| **Citation** | Document Parser 1 | citation_alignment_score < 0.80 1 | Bracketed citations do not map to verified source page coordinates.2 | document.score 1 |
| **Retrieval** | Index / Search 1 | MRR@k < 0.50 1 | Empty result sets or irrelevant documents returned for queries.1 | retrieval.latency 1 |
| **Corpus** | Ingestion Storage 2 | Ingestion validation failure 2 | Attacker-controlled documents enter index, overriding system prompts.2 | origin_source_type 2 |
| **Tool** | Agent / Executor 1 | json_decode_error 1 | Agent invokes external APIs with malformed, ungrounded, or unsafe parameters.1 | gen_ai.tool.name 1 |
| **Routing** | Gateway Proxy 1 | selected_model mismatch 1 | Silent downgrades shift traffic below the specified model quality floor.3 | routing_reason 1 |
| **Policy** | Guardrail / Filter 2 | policy_violation_rate trigger 2 | Model overblocks benign queries or fails to intercept policy violations.2 | guardrail.id 1 |
| **UI / Trust** | Interface Display 3 | average_approval_ms < 250ms 1 | System hides uncertainty, encouraging uncritical user overreliance.3 | citation_click_rate 1 |
| **Governance** | Compliance / Audit 1 | Signature validation failure 2 | Deployed pipelines execute mutations without valid cryptographic signatures.2 | maker_id / checker_id 1 |
| **Model** | Inference Serving 1 | reconstruction_error spike 1 | Silent degradation in reasoning performance following provider updates.2 | canary_similarity_score 1 |
| **Agent-Loop** | Orchestration 2 | state_repetition_count > 2 1 | Multi-agent pipelines enter infinite planning or formatting repair loops.2 | repair_loop_count 1 |
| **Cost** | Billing / Resource 1 | cost_velocity_usd > limit 1 | High-frequency token consumption or runaway API invocations.2 | usage.cost.total 1 |
| **Security** | Boundary / Access 2 | Unapproved network egress 2 | Compromised MCP tool server executes arbitrary remote commands.2 | rpc.response.status_code 1 |
| **Privacy** | Isolation / Cache 2 | Cross-tenant cache hits 2 | Cross-tenant data leaks or cached state contamination across user boundaries.2 | stale_cache_served 1 |
| **Human-Review** | Operational Queue 1 | review_duration_seconds spike 1 | Expert review queues become saturated, forcing automation defaults.3 | approval_requests.id 1 |

## **AI Severity Model**

AI severity must be consequence-driven, not symptom-driven. The same failure class can be harmless in staging, severe in a regulated production workflow, or catastrophic when it reaches an autonomous tool surface. Severity is therefore assigned by combining harm type, exposure, reversibility, active propagation, regulatory sensitivity, and confidence in detection.

```text
severity = f(
  harm_type,
  affected_population,
  exposure_count,
  active_propagation,
  reversibility,
  security_or_regulatory_sensitivity,
  confidence_of_detection
)
```

Severity assignment should be reviewed when new evidence changes the blast radius or reversibility estimate. Operators should prefer temporary over-classification during uncertainty and downgrade only after containment and scope validation.

| Severity Level | Consequence Envelope | Typical AI Failure Examples | Immediate Response | Recovery / Closure Criteria |
| :---- | :---- | :---- | :---- | :---- |
| **SEV-0** | Active or imminent irreversible harm, uncontrolled high-impact autonomous action, confirmed cross-tenant exposure at broad scope, or severe security compromise with ongoing propagation. | Unauthorized destructive tool execution, confirmed regulated-data leak across tenants, fail-open bypass of core authorization, uncontrolled agentic action against critical systems. | Activate global or scoped kill switch; freeze affected capability; page incident commander, security, privacy, operations, and executive sponsor as applicable. | Harm is contained, affected scope is verified, exposed credentials/artifacts are revoked or quarantined, and recovery route passes high-risk validation. |
| **SEV-1** | Active high-impact harm or high-confidence risk affecting a tenant, workflow, regulated domain, or state-changing tool surface. Harm is serious but containable. | Ungrounded high-impact advice delivered to active users, unauthorized mutation attempt blocked late, tenant-scoped data exposure, poisoned retrieval route influencing production answers. | Isolate affected tenant/route/tool/index; revoke scoped credentials; preserve evidence; switch to safe degraded mode or fail closed. | Blast radius is known, active harm has stopped, affected users/workflows are identified, and compensating or corrective actions are underway. |
| **SEV-2** | Contained semantic, retrieval, model, policy, or tool failure with limited blast radius and no confirmed irreversible external harm. | Citation failures in production, schema drift causing blocked actions, model regression on bounded workflow, repeated tool argument rejection, contained prompt-injection success without side effect. | Disable or downgrade affected route; apply feature flag; route to verified cache, manual review, or bounded degraded mode. | Regression test covers the failure; telemetry confirms no recurrence over the required observation window. |
| **SEV-3** | Quality, latency, cost, or trust degradation visible to limited users but without safety, privacy, or high-impact action exposure. | Model route downgrade disclosed to users, elevated unsupported-claim rate in low-risk domain, parser degradation, stale cache served with proper labeling. | Communicate limitation; preserve state; reduce capability if needed; monitor for escalation. | Service returns to expected behavioral envelope and user-visible degradation is resolved or accepted by policy. |
| **SEV-4** | Internal anomaly, evaluation regression, telemetry drift, suspicious signal, or staging failure with no confirmed user impact. | Canary drift, golden-set failure, evaluation drop, prompt-template compile warning, non-production index anomaly. | Open tracked operations issue; assign owner; block release if policy requires. | Root cause is documented or accepted, and release gates or monitoring are updated if needed. |

Severity should never be determined by a single metric alone. A low grounding score, citation score, cost spike, or routing mismatch is a signal. It becomes an incident severity level only after operators estimate consequence, exposure, active propagation, reversibility, and confidence.

## **Detection and Intake Model**

AI operations requires a structured, multi-channel Detection and Intake Model to route anomalies to the correct SRE responder queues.18 Anomalies are ingested automatically from strategic telemetry monitors, CI/CD evaluation gate failures, or customer-reported support tickets.1

  Strategic Telemetry ───► Anomaly Detector ──┐  
  CI/CD Eval Gates    ───► Regression Gate ──┼──► [Intake Controller] ──► Preserves Verification Artifacts ──► Pages On-Call SRE  
  Support Desk        ───► Escalation Queue ─┘

The intake schema enforces immediate field mapping to preserve the semantic state of the interaction, preventing forensic data loss during the initial triage window:

* **Reporter Identity:** System ID, User ID, or support ticket reference.  
* **Ingestion Timestamp:** Monotonic UTC timestamp of the first detected anomaly.  
* **Affected Workspace ID:** UUID mapping the failure to a specific tenant partition.2  
* **Observed Pathology Class:** Categorized target from the AI Incident Taxonomy.2  
* **Trace Context Identifier:** W3C Trace Parent string and active parent-span ID.1  
* **Active Model Manifest Hash:** Cryptographic signature verifying active weight versions.2  
* **Active Prompt Version:** Semantic version of the compiled template.3  
* **Retrieval Snapshot Path:** Secure reference link pointing to S3-archived document vectors.1  
* **Containment Status Flag:** Boolean tracking whether automated circuit breakers have triggered.2

### **Evidence Preservation During Intake**

Containment actions must not destroy evidence required for scope analysis, replay, attribution, legal review, or regulatory reporting. Before clearing caches, wiping sessions, redeploying containers, rotating credentials, rebuilding indexes, or mutating prompt routes, the intake controller should preserve a minimal tamper-evident incident manifest containing trace identifiers, artifact hashes, active configuration versions, relevant secure payload references, policy decisions, and containment actions. Raw sensitive payloads should not be copied into general incident tickets; they should be stored only through controlled forensic references with access logs and retention policy.

Upon ingestion of a serious or catastrophic incident (SEV-0 or SEV-1), the intake controller issues an automated command to lock the active session, seal related model adapters, snapshot the active index state, and write a tamper-evident reference manifest to the compliance-audit database, preventing operators from clearing caches or redeploying code before forensics are complete.2

## **Semantic Triage Tree**

Semantic triage identifies the failing operational layer before responders choose a containment or rollback surface. The goal is to avoid the two classic incident sins: rolling back the wrong component because it was visible, and destroying forensic evidence because someone panic-clicked “clear cache.” Charming hobbies, both. Not operations.

```text
SEMANTIC TRIAGE TREE

[ Incident Intake ]
        |
        v
[ 1. Is there active safety, privacy, financial, legal, or security harm? ]
        |
        +-- yes --> [ Contain first ]
        |             isolate route/tool/tenant/index/cache
        |             revoke scoped credentials if needed
        |             preserve evidence manifest
        |
        +-- no  --> continue triage
        |
        v
[ 2. Did a state-changing tool or external action execute or possibly execute? ]
        |
        +-- yes --> [ Tool / Action Branch ]
        |             hold unknown state
        |             reconcile source of record
        |             compensate only committed reversible effects
        |
        +-- no  --> continue triage
        |
        v
[ 3. Is retrieved evidence, citation, corpus, or cache state implicated? ]
        |
        +-- yes --> [ Retrieval / Corpus Branch ]
        |             freeze ingestion
        |             quarantine suspect sources
        |             bypass unsafe cache
        |             rebuild or re-rank from verified manifest
        |
        +-- no  --> continue triage
        |
        v
[ 4. Is the model route, adapter, decoding policy, or provider behavior implicated? ]
        |
        +-- yes --> [ Model / Routing Branch ]
        |             pin known-good route
        |             disable suspect adapter
        |             run canary and regression profile
        |
        +-- no  --> continue triage
        |
        v
[ 5. Is prompt, policy, schema, or tool-description behavior implicated? ]
        |
        +-- yes --> [ Prompt / Policy / Contract Branch ]
        |             revert template or policy bundle
        |             apply bounded prompt hotfix if needed
        |             validate against targeted incident evals
        |
        +-- no  --> continue triage
        |
        v
[ 6. Is the failure primarily user-facing disclosure, review, or trust calibration? ]
        |
        +-- yes --> [ UX / Review / Governance Branch ]
        |             disclose limitation
        |             pause high-impact automation
        |             route to review or approval queue
        |
        +-- no  --> [ Unknown / Multi-Layer Branch ]
                      preserve full evidence manifest
                      keep containment active
                      assign cross-functional incident review
```

| Branch | Diagnostic Artifacts | Immediate Containment | Likely Rollback / Recovery Surface |
| :---- | :---- | :---- | :---- |
| **Tool / Action** | Tool trace, authorization decision, idempotency key hash, pre/post state hash, source-of-record status. | Disable affected tool, hold workflow, block blind retry, revoke scoped credentials if compromised. | Tool contract, tool route, credential scope, compensation workflow, idempotency ledger. |
| **Retrieval / Corpus** | Retrieval trace, source IDs, source version hashes, chunk IDs, cache scope, citation verification state. | Freeze ingestion, quarantine suspect documents, bypass unsafe cache, block suspect source lifecycle states. | Corpus lifecycle state, index manifest, chunking policy, retrieval filter, cache key version. |
| **Model / Routing** | Model route, provider profile, model/version hash where available, adapter manifest, decoding config, canary deltas. | Pin known-good route, disable suspect adapter, reduce autonomy, enter disclosed degraded mode. | Model route manifest, adapter binding, decoding profile, provider fallback policy. |
| **Prompt / Policy / Contract** | Rendered prompt reference, prompt version, policy bundle version, schema version, validation errors. | Revert prompt/policy/schema exposure, disable risky prompt path, apply bounded hotfix. | Prompt template, policy bundle, tool description, schema registry, validator. |
| **UX / Review / Governance** | Disclosure event, approval record, reviewer dwell time, escalation packet, user correction signal. | Show status, pause high-impact automation, route to review, block auto-approval. | Review rules, disclosure policy, approval thresholds, UI trust calibration. |
| **Unknown / Multi-Layer** | Full trace graph, incident manifest, secure payload refs, configuration versions, containment actions. | Maintain containment until narrowed; avoid destructive cleanup. | Determined after forensics. |


## **Incident Evidence Package**

The Incident Evidence Package is the forensic bundle used to scope, replay, audit, and repair an AI incident. Raw syslogs are not enough for probabilistic systems, but unrestricted raw prompt dumps are also not acceptable. The package must preserve enough evidence to reconstruct decisions without turning the incident tracker into a second data breach wearing a little lanyard.

```text
INCIDENT EVIDENCE PACKAGE

[ Incident ID ]
      |
      +--> Trace and Span References
      |      trace_id, span_ids, workflow_id, session_hash, tenant_hash
      |
      +--> Runtime Configuration
      |      model route, provider profile, prompt version, policy version,
      |      schema version, tool manifest hash, gateway route manifest
      |
      +--> Evidence and Retrieval State
      |      source IDs, source version hashes, chunk IDs, retrieval IDs,
      |      cache scope, citation coordinates where applicable
      |
      +--> Action and Tool State
      |      tool call ID, payload hash, idempotency key hash,
      |      authorization decision, pre/post state hashes, verification status
      |
      +--> Supply-Chain and Deployment State
      |      artifact hashes, image digest, model/adaptor signatures,
      |      dependency manifest, sandbox profile
      |
      +--> Secure Payload References
      |      access-controlled references to raw prompts, outputs, files,
      |      tool payloads, and sensitive evidence when retention is allowed
      |
      +--> Containment and Recovery Record
             feature flags, kill switches, credential revocations,
             quarantines, rollbacks, compensations, notifications
```

| Evidence Dimension | Preserve By Default | Sensitive Payload Handling | Operational Purpose |
| :---- | :---- | :---- | :---- |
| **Trace Context** | W3C `traceparent`, span IDs, workflow ID, route ID, incident ID. | Safe as metadata if tenant/user identifiers are hashed or opaque. | Reconstruct execution chronology. |
| **Model and Prompt State** | Model route, provider profile, adapter manifest, decoding config, prompt template ID, rendered prompt hash. | Rendered prompt text stored only as secure reference when needed. | Identify model, prompt, or routing regression. |
| **Retrieval State** | Retrieval ID, query hash, source IDs, chunk IDs, source version hashes, citation regions, authorization filter version. | Raw retrieved text stored as secure evidence reference, not in general tickets. | Diagnose grounding, citation, stale-source, or leakage failures. |
| **Tool / Action State** | Tool name/version, schema version, payload hash, idempotency key hash, approval status, pre/post state hashes. | Raw arguments and results stored only in action ledger or forensic vault. | Determine whether action executed, failed, partially committed, or remains unknown. |
| **Policy and Authorization** | Policy bundle version, decision ID, denial/allow class, scoped credential lifetime, approval requirement. | Do not log raw credentials, auth headers, bearer tokens, or private policy secrets. | Prove whether the action was authorized. |
| **Supply-Chain Artifacts** | Container image digest, dependency manifest, model/adaptor hash, signature status, sandbox profile. | Store signature bundles and manifests; avoid copying private keys or secrets. | Prove what artifact executed. |
| **User-Facing State** | Disclosure shown, status message ID, user confirmation state, escalation package ID. | Store user-visible text by secure reference when sensitive. | Determine whether users were properly informed. |
| **Containment Actions** | Flag toggles, kill-switch activation, index quarantine, cache bypass, route rollback, credential revocation. | No secret values; store action IDs and affected scopes. | Prove containment timing and scope. |

### **Evidence Handling Rule**

```text
General incident record:
  hashes, IDs, versions, policy decisions, redacted summaries, secure refs.

Controlled forensic vault:
  raw prompts, raw outputs, source excerpts, uploaded files, tool payloads,
  transaction details, and other sensitive incident evidence.

Never store raw credentials, bearer tokens, private keys, or unrestricted
tenant data in ordinary tickets, logs, or postmortem documents.
```

## **AI Incident Command Role Model**

AI incidents cross model behavior, retrieval, tools, user trust, privacy, security, governance, and infrastructure. Incident response therefore requires role separation. The incident commander owns coordination and severity. Domain owners diagnose and execute bounded changes. Governance, privacy, legal, and communications roles control regulated obligations and external messaging.

```text
AI INCIDENT COMMAND STRUCTURE

                     [ Incident Commander ]
                              |
       +----------------------+----------------------+
       |                      |                      |
[ Technical Response ] [ Risk / Governance ] [ User / Business Response ]
       |                      |                      |
AI Ops Lead            Security Lead          Customer Comms Lead
Model Owner            Privacy Lead           Support Lead
Prompt Owner           Governance Lead        Executive Sponsor
Retrieval Owner        Legal Liaison
Tool/Action Owner
SRE/Platform Lead
Evaluation Lead
```

| Role | Primary Responsibility | Authorized Actions | Escalates When |
| :---- | :---- | :---- | :---- |
| **Incident Commander** | Owns coordination, severity, response cadence, decision log, and closure criteria. | Activates kill switches, assigns owners, approves containment scope, declares behavioral recovery. | SEV-0/SEV-1, unclear ownership, public/regulatory exposure, prolonged containment. |
| **AI Operations Lead** | Owns gateway routing, fallback, model/provider route health, and degraded-mode operation. | Pins routes, changes traffic splits, disables unsafe model paths, coordinates with SRE. | Routing changes affect quality floor, safety, privacy, or broad user cohorts. |
| **SRE / Platform Lead** | Owns serving infrastructure, queues, GPU capacity, deployment health, and runtime stability. | Scales serving pools, isolates pods/nodes, rolls back deployment images, enforces circuit breakers. | Infrastructure failure contributes to semantic or user-visible incident. |
| **Model Owner** | Owns model snapshots, provider profiles, adapters, quantization configs, and decoding profiles. | Disables adapters, pins model snapshot, changes approved decoding profile, initiates model regression evaluation. | Model behavior drift, provider update, adapter failure, or route quality regression is suspected. |
| **Prompt Owner** | Owns system prompts, tool descriptions, safety wrappers, and prompt registry changes. | Reverts prompt versions, proposes emergency hotfix, validates placeholder and policy invariants. | Prompt injection, instruction loss, schema drift, or template regression is implicated. |
| **Retrieval / Corpus Owner** | Owns corpus lifecycle, chunking, embeddings, vector indexes, source authority, and cache eligibility. | Freezes ingestion, quarantines sources, rebuilds index from manifest, updates retrieval eligibility state. | Poisoning, stale evidence, citation failure, or cross-tenant retrieval is suspected. |
| **Tool / Action Owner** | Owns tool contracts, scoped credentials, idempotency, action ledgers, and post-action verification. | Revokes tool credentials, disables tool route, blocks blind retry, initiates reconciliation or compensation. | State-changing action is executed, unknown, duplicated, unauthorized, or misreported. |
| **Security Lead** | Owns prompt-injection compromise, SSRF, RCE, egress, sandbox, secret leakage, and adversarial activity. | Blocks egress, isolates runtimes, rotates exposed credentials, directs forensic capture. | Boundary violation, malicious artifact, unauthorized tool use, or active exploit is detected. |
| **Privacy Lead** | Owns PII/PHI exposure, tenant leakage, cache contamination, and privacy-impact assessment. | Freezes affected data scopes, requires secure evidence handling, coordinates affected-scope analysis. | Personal, regulated, or tenant-private data may have been exposed. |
| **Governance / Compliance Lead** | Owns policy obligations, regulated incident thresholds, audit artifacts, and required reporting workflows. | Determines governance review path, coordinates regulatory reporting where legally required. | Incident may trigger contractual, regulatory, audit, or internal governance obligations. |
| **Legal Liaison** | Advises on liability, privilege, preservation duties, notification risk, and external legal exposure. | Recommends legal hold, reviews communications, coordinates with counsel. | Potential harm, regulated disclosure, litigation risk, or contractual breach is present. |
| **Customer Communications Lead** | Owns status page, customer-facing language, support scripts, and disclosure consistency. | Publishes approved updates, coordinates user notices, avoids unverified claims. | User-visible degradation, breach notification, SLA issue, or public-facing incident occurs. |
| **Support Lead** | Owns ticket routing, user reports, support scripts, and frontline escalation. | Escalates patterns to IC, updates support guidance, coordinates user-level remediation. | Support tickets spike, users report false success, or manual recovery is needed. |
| **Evaluation Lead** | Owns incident-to-eval promotion, regression reproduction, golden cases, and release gates. | Converts sanitized incident traces into test cases, blocks release on unresolved regression. | Incident class lacks adequate eval coverage or repair needs release verification. |
| **Executive Sponsor** | Owns executive decision-making for catastrophic public, regulatory, financial, or safety incidents. | Approves major public posture, business-continuity actions, and broad shutdown decisions. | Incident materially affects customers, regulators, revenue, safety, or public trust. |

## **Containment Strategy**

Containment means stopping active harm before the definitive root cause is identified.2 Probabilistic systems require a graduated containment progression to limit the blast radius while preserving task continuity for unaffected enterprise tenants 2:

```
  Incident Ingested ──► Map blast radius to session contexts  
                             │  
                             ▼  
  Local Containment  ──► Tenant Partition / Isolate Namespace   
                             │  
                             ▼  
  Scoped Containment ──► Toggle Flag / Revoke Tool Scope   
                             │  
                             ▼  
  System Failover    ──► Route Fallback / Fail-Closed 
```

### **1. Identify and Scope the Failure**

Upon alert ingestion, the responder identifies the smallest affected perimeter.2 If a failure impacts only a single workspace, the responder isolates that tenant's namespace inside pgvector and Redis caches, preventing global service disruption.2

### **2. Isolate via Capability Kill Switches**

If the failure involves agentic tool execution (such as recursive database writes), the responder toggles the corresponding feature flag, disabling write actions while preserving read-only informational capability.2

### **3. Route to Safe Degraded Modes**

If cognitive performance has degraded globally, the gateway proxy intercepts downstream requests, shifting traffic to smaller, cached, or local model configurations.3 The system displays a plain-language disclosure, informing the user that advanced analytical capabilities are temporarily restricted.3

### **4. Fail-Closed Enforcement**

If containment paths cannot satisfy the system's defined safety, privacy, or compliance floors, the transaction is terminated.2 All active session credentials are revoked, in-flight database transactions are rolled back, and the system freezes safely to prevent cascading failures.2

## **Feature Flag and Kill Switch Matrix**

Feature flags and kill switches must operate strictly outside the model's cognitive boundary, utilizing centralized gateway routing weights or isolated container-level network proxies to enforce boundaries.2

```
  Requests ──► Filter checks (OIDC JWT verified)  
                     │  
                     ├─► FF_MODEL_ROUTE ( claude-3-5-sonnet -> claude-3-5-haiku )   
                     ├─► FF_TOOL_REVOKE ( Revokes OAuth token inside vault )   
                     └─► FF_INDEX_FREEZE ( Sets HNSW partition to read-only ) 
```

The Feature Flag and Kill Switch Matrix outlines the technical implementation, operational check, and restoration procedure for each control:

| Switch Identifier | Scope of Control | Underlying Code Mechanism | Access Control Rule (RBAC) | Standard Restoration Criteria |
| :---- | :---- | :---- | :---- | :---- |
| **FF_GLOBAL_AI** | Global Platform | Gateway proxy routing configuration toggle.2 | Platform Administrator | 100% pass on CI/CD validation gates.1 |
| **FF_TENANT_BLOCK** | Specific Workspace | Redis key block; database RLS filter constraint.2 | Incident Commander 17 | Security compliance sign-off on tenant files.2 |
| **FF_TOOL_REVOKE** | Specific Agent API | OAuth token revocation inside Secrets Manager.2 | Tool Owner | API status matches baseline schemas.2 |
| **FF_MODEL_ROUTE** | Serving Endpoint | Gateway routing weight redistribution.3 | AI Operations Lead | 10-run canary suite perplexity matches baseline.2 |
| **FF_INDEX_FREEZE** | Document Indexing | Ingestion worker write lock; HNSW read-only flag.2 | Retrieval Owner | HubScan robust z-score returns to normal (less than 5.0).2 |
| **FF_CACHE_BYPASS** | Semantic Memory | Redis cache lookup bypass configuration.2 | SRE On-Call Engineer | Cache keys cleared; TTL parameters updated.2 |
| **FF_AGENT_DRAFT** | Agent Loop Autonomy | Blocks auto-send; forces read-only draft views.2 | Prompt Owner | Trajectory evaluation pass rate > 95%.1 |

## **Rollback Surface Map**

Rollback in AI systems is multi-surface. Reverting the model while leaving a poisoned index, stale cache, incompatible prompt, or drifted tool schema active can create a new incident. Operators must identify the smallest effective rollback surface and validate all coupled artifacts before restoring traffic.

```text
ROLLBACK SURFACE MAP

[ User-visible or telemetry-detected failure ]
        |
        v
[ Identify failing surface ]
        |
        +--> prompt template / tool description
        +--> model route / provider profile / adapter
        +--> retrieval index / corpus lifecycle state
        +--> policy bundle / authorization rule
        +--> tool contract / action gateway
        +--> cache key scope / semantic cache
        +--> UI control / disclosure / automation locator
        +--> deployment image / dependency / sandbox profile
        |
        v
[ Preserve evidence manifest ]
        |
        v
[ Apply smallest safe rollback or containment ]
        |
        v
[ Run surface-specific validation ]
        |
        v
[ Restore traffic gradually or remain degraded/fail-closed ]
```

| Rollback Surface | Mechanical Trigger | Evidence to Capture Before Change | Validation Before Restoration | Common Failure Mode |
| :---- | :---- | :---- | :---- | :---- |
| **Prompt Template / Tool Description** | Reassign active prompt/template tag to previous approved version. | Prompt ID, rendered prompt hash, template version, variables, failing output hash. | Prompt compile check, safety/policy invariants, targeted incident evals. | Placeholder mismatch, instruction regression, hidden tool-description drift. |
| **Model Route / Provider Profile** | Pin gateway route to previous approved model/provider snapshot or serving profile. | Route ID, provider response metadata, model snapshot/hash where available, decoding config. | Canary suite, schema pass rate, grounding checks, latency/cost profile. | Capability loss, context-window mismatch, provider SDK incompatibility. |
| **Adapter / LoRA / Fine-Tune** | Disable suspect adapter or revert to previous adapter manifest. | Adapter hash, parent model ID, tenant binding, training dataset lineage. | Tenant-scoped regression suite and behavior comparison against base route. | Adapter dimension mismatch, cross-tenant adapter exposure, quality regression. |
| **Retrieval Index** | Restore index from verified manifest or rebuild from authorized source records. | Source IDs, chunk IDs, embedding model version, index manifest, query traces. | Retrieval MRR/recall checks, authorization checks, citation verification. | Missing vectors, stale source lifecycle state, HNSW rebuild delay. |
| **Corpus Lifecycle State** | Mark suspect source/chunk/vector as quarantined, revoked, stale, or inactive. | Source version hash, ingestion batch ID, parser version, transformation history. | Retrieval eligibility tests and source-authority checks. | Quarantine bypass through cache or derived summary. |
| **Policy Bundle** | Revert OPA/policy-as-code bundle or authorization rules. | Policy version, decision logs, rule IDs, affected scopes. | Policy compile check, adversarial tests, false-positive/false-negative smoke tests. | Overblocking, underblocking, mismatch between UI disclosure and policy. |
| **Tool Contract / Action Gateway** | Revert tool schema, MCP manifest, OpenAPI contract, or wrapper logic. | Tool manifest hash, payload hash, validation errors, authorization decision. | Dry-run validation, idempotency test, post-action verification test. | Downstream API changed; old schema no longer matches target service. |
| **Semantic / Prefix Cache** | Bypass, invalidate, or version cache key scope. | Cache key hashes, tenant/session scope, source/policy/model versions. | Scope-isolation test, freshness test, live retrieval confirmation. | Thundering-herd load, stale cache re-entry, cross-scope key reuse. |
| **UI / Trust Control** | Revert disclosure labels, approval gate behavior, browser locators, or citation rendering. | Screenshot hash, DOM snapshot hash, disclosure state, click/action logs. | UI regression test, disclosure check, automation re-observation test. | Silent downgrade, incorrect confidence, blind-click automation. |
| **Deployment Image / Runtime** | Revert container image, dependency lockfile, parser sandbox, or serving image. | Image digest, SBOM/AI-BOM refs, sandbox profile, CVE/signature status. | Vulnerability scan, smoke test, sandbox policy test, health + behavior canary. | Reintroducing vulnerable dependency or breaking model-loader compatibility. |

## **Prompt Hotfix Protocol**

Prompt hotfixes are emergency mitigations, not magic patches. They may reduce active harm while a durable fix is prepared, but they must be versioned, reviewed, tested, and retired or promoted through the normal release process. A prompt hotfix that cannot be audited is just production improv with a YAML costume.

```text
PROMPT HOTFIX FLOW

[ Active prompt-related incident ]
        |
        v
[ Create incident-bound hotfix branch ]
        |
        v
[ Preserve failing trace + rendered prompt reference ]
        |
        v
[ Apply minimal prompt/template/tool-description change ]
        |
        v
[ Pre-flight validation ]
  placeholders | token budget | schema references | policy invariants
        |
        v
[ Risk-tiered eval gate ]
  targeted incident cases | safety probes | schema checks | grounding checks
        |
        v
[ Controlled exposure ]
  canary, tenant-scoped route, or internal-only validation
        |
        v
[ Promote, revise, or revert ]
        |
        v
[ Add incident case to permanent evals ]
```

| Gate | Required Check | Failure Handling |
| :---- | :---- | :---- |
| **Incident Binding** | Hotfix branch, prompt version, and deployment record reference the incident ID. | Block deployment if change is not traceable to incident. |
| **Minimality Review** | Change addresses the active failure without broad unrelated behavior changes. | Split unrelated improvements into normal release path. |
| **Template Integrity** | Variables, tool names, delimiters, schemas, and context-budget assumptions remain valid. | Reject hotfix until compiler and schema checks pass. |
| **Policy Invariants** | Safety, privacy, authority hierarchy, and tool-boundary instructions are not weakened. | Fail closed; route to policy owner or security lead. |
| **Targeted Regression** | Incident-triggering case and related variants pass. | Keep containment active; revise or roll back. |
| **Canary / Exposure Control** | Exposure is bounded by risk tier, tenant scope, and rollback readiness. | Disable route if metrics degrade or unexpected behavior appears. |
| **Promotion / Retirement** | Hotfix is either promoted into a normal release with tests or retired after durable fix. | Emergency-only prompt changes cannot remain unowned indefinitely. |

Specific thresholds such as number of eval cases, canary percentage, and observation window should be set by risk tier and deployment profile. High-impact workflows require stricter approval and lower exposure than low-risk conversational formatting fixes.

## **Model Rollback Model**

Model rollback restores a prior approved serving behavior by changing the model route, provider profile, adapter binding, decoding profile, or serving image. It should be executed at the gateway or serving-control layer so downstream applications do not hardcode emergency model logic.

```text
MODEL ROLLBACK MODEL

[ Drift / regression / provider incident detected ]
        |
        v
[ Freeze route manifest and preserve evidence ]
        |
        v
[ Identify rollback target ]
  previous provider profile
  approved model snapshot
  prior adapter manifest
  conservative decoding profile
  last stable serving image
        |
        v
[ Route traffic to rollback target ]
        |
        v
[ Run validation suite ]
  schema | grounding | policy | tool compatibility | latency | cost
        |
        v
[ Restore gradually or remain degraded/fail-closed ]
```

| Rollback Dimension | What Changes | Validation Required | Common Risk |
| :---- | :---- | :---- | :---- |
| **Provider Route** | Gateway selects previous approved provider/model profile. | Capability floor, safety profile, context window, schema support. | Silent downgrade below task requirements. |
| **Model Snapshot** | Self-hosted or registry-managed model reverts to prior signed snapshot. | Signature/hash check, canary behavior, latency, memory footprint. | Snapshot incompatible with current tokenizer, adapter, or prompt. |
| **Adapter / LoRA** | Suspect adapter is disabled or reverted to prior manifest. | Parent-model compatibility, tenant binding, targeted task eval. | Quality drop or accidental cross-tenant adapter exposure. |
| **Decoding Profile** | Temperature, top-p, max tokens, constrained decoding, or structured-output mode changes. | Schema pass rate, semantic quality, refusal behavior, output length. | Overcorrection causing refusals, truncation, or loss of usefulness. |
| **Serving Image** | Runtime container, model loader, dependency set, or quantization profile changes. | Smoke test, model-load verification, CVE/signature check, performance envelope. | Reintroducing vulnerable loaders or incompatible kernels. |
| **Prompt Coupling** | Prompt route is pinned to a compatible version for rollback route. | Prompt-template compile, tool description compatibility, context budget. | Old model receives prompt format it cannot follow. |

Rollback closure requires behavioral validation, not merely successful deployment. A route is recovered only when task-level outputs return to the approved envelope for grounding, schema, policy, latency, tool compatibility, and user-facing disclosure.


## **Corpus Quarantine and Retrieval Rollback Model**

Retrieval incidents are contained by changing source eligibility, not by trusting the model to ignore bad evidence. Poisoned, stale, unauthorized, or anomalous documents must be removed from the retrieval candidate set through database-enforced lifecycle state, tenant scope, source authority, and cache invalidation.

```text
CORPUS QUARANTINE FLOW

[ Retrieval anomaly detected ]
  hubness | stale source | cross-tenant hit | citation mismatch | user report
        |
        v
[ Preserve retrieval evidence ]
  retrieval_id, query_hash, source IDs, chunk IDs, cache scope, index manifest
        |
        v
[ Mark affected artifacts ]
  source_lifecycle_state = quarantined / revoked / stale / pending_review
        |
        v
[ Enforce retrieval eligibility ]
  tenant scope + ACL + source state + policy version + cache scope
        |
        v
[ Freeze affected ingestion path ]
        |
        v
[ Serve safe fallback ]
  lexical search | verified cache | partial answer | review | fail closed
        |
        v
[ Rebuild or repair index from verified manifest ]
```

| Control | Purpose | Implementation Pattern |
| :---- | :---- | :---- |
| **Source Lifecycle State** | Blocks suspect sources and derived chunks from active retrieval. | Store lifecycle state such as `active`, `pending_review`, `quarantined`, `revoked`, or `stale`; retrieval queries admit only eligible states. |
| **Tenant and ACL Enforcement** | Prevents cross-tenant or unauthorized retrieval during incident response. | Enforce DB-level RLS or equivalent authorization before candidate scoring. |
| **Quarantine Registry** | Provides fast emergency exclusion without ad hoc SQL string injection. | Maintain tenant-scoped denylist/quarantine table joined by source ID, chunk ID, or vector ID. |
| **Cache Invalidation / Bypass** | Prevents quarantined evidence from reappearing through stale cache. | Version cache keys by source, policy, tenant, and retrieval manifest; bypass or invalidate affected scopes. |
| **Index Rebuild Manifest** | Restores index topology from known-good source/chunk/vector versions. | Rebuild affected partition from signed or approved manifest; validate embedding model and dimensions. |
| **Fallback Retrieval** | Preserves limited usability during vector repair. | Use lexical/BM25 search, verified cache, partial answer, or manual review depending on risk. |

Hubness, citation mismatch, and retrieval anomalies should be treated as triage signals. A high robust z-score or unusual hit frequency does not prove malicious poisoning by itself; it justifies quarantine, review, and replay against representative query sets.


## **Tool and Action Containment Model**

Tool incidents are dangerous because probabilistic planning crosses into deterministic side effects. The operational rule is simple: never let conversational confidence outrun verified action state.

```text
TOOL AND ACTION CONTAINMENT

[ Proposed Action ]
        |
        v
[ Validate Payload ]
  schema | semantic rules | policy | tenant/user scope
        |
        v
[ Authorize Action ]
  scoped credential | approval state | risk class
        |
        v
[ Create Idempotency Record ]
  request hash | action ID | actor | target | timestamp
        |
        v
[ Capture Pre-Action State Hash ]
        |
        v
[ Execute or Block ]
        |
        v
[ Observe Tool Result ]
        |
        v
[ Verify Source of Record ]
        |
        +--> verified success  -> report success
        +--> verified failure  -> report failure / preserve draft
        +--> unknown state     -> hold and reconcile
        +--> partial commit    -> compensate or forward recover
```

| Incident State | Meaning | Correct Operational Response | User-Facing Status |
| :---- | :---- | :---- | :---- |
| **Blocked Before Execution** | Payload, policy, approval, or authorization check failed. | Do not call tool; preserve draft and validation error. | “Not submitted. This action was blocked before execution.” |
| **Execution Failed Before Commit** | Tool rejected or failed before external state changed. | Preserve error and allow safe correction or retry if preconditions still hold. | “The action failed before completion.” |
| **Unknown After Attempt** | Timeout, lost response, or ambiguous observation after a state-changing call. | Hold workflow; reconcile with source of record before retry. | “Status unknown. We are verifying before allowing another attempt.” |
| **Partial Commit** | Some sub-actions committed while others failed. | Stop dependent actions; compensate reversible steps or forward recover if safer. | “Some steps completed; remaining steps are paused for verification.” |
| **Committed Reversible Effect** | External state changed and compensation is supported. | Execute approved compensation workflow if reversal is required. | “The action completed and is being reversed through a tracked correction.” |
| **Committed Irreversible Effect** | Pivot transaction succeeded and cannot be programmatically undone. | Stop further automation; notify responsible owners; begin remediation and communication. | “The action completed and requires manual review/remediation.” |
| **False Success Claim** | UI/model claimed completion before verification. | Correct status, preserve claim evidence, open incident if user impact exists. | “Correction: the previous completion status was not verified.” |

Rollback applies only inside a live transaction boundary. Once a side effect has committed, operators should use compensation, forward recovery, reconciliation, or manual remediation depending on the transaction state.

## **Cache, Cost, and Resource Incident Model**

Resource incidents occur when model calls, retries, cache behavior, retrieval fan-out, tool loops, or agentic planning consume capacity faster than the system can safely serve users. These incidents can cause denial-of-wallet, latency collapse, stale-cache exposure, and degraded user trust.

```text
RESOURCE INCIDENT CONTROL LOOP

[ Active workflow ]
        |
        v
[ Measure resource state ]
  tokens | tool calls | retries | latency | queue depth | spend | cache scope
        |
        v
[ Compare against profile budget ]
  tenant | session | workflow | risk tier | route
        |
        +-- within budget --> continue
        |
        +-- warning band --> degrade, queue, prune, or ask user
        |
        +-- hard limit --> halt, preserve state, fail closed or escalate
```

| Resource Failure | Detection Signal | Containment | Recovery |
| :---- | :---- | :---- | :---- |
| **Runaway Agent Loop** | Repeated state hash, tool repetition, growing turn count, no-progress plan diffs. | Halt workflow, preserve state, block further tool calls. | Replan from verified state or escalate. |
| **Repair Loop** | Repeated schema/format failures with similar payloads. | Stop bounded repair after profile limit. | Return structured failure or route to human review. |
| **Retry Storm** | High retry count, queue depth spike, provider 429/5xx, synchronized backoff failure. | Circuit-break route; apply jitter/backoff; shed or queue traffic. | Restore gradually after provider/gateway health recovers. |
| **Token / Spend Spike** | Cost velocity exceeds tenant/workflow budget band. | Freeze expensive route, reduce context, require approval, or fail closed. | Tune prompt/context, adjust budgets, add loop regression test. |
| **Cache Scope Violation** | Cache hit with tenant/user/policy/source mismatch. | Disable affected cache scope; revoke exposed sessions if needed. | Rebuild cache namespace and add isolation test. |
| **Stale Cache Overuse** | Cache served after source/policy/model version change. | Bypass or invalidate stale keys; disclose limitation if served safely. | Version cache by source, policy, model, prompt, and risk profile. |
| **Prefill / Context Pressure** | Long prompt, rising TTFT, low evidence density, context overflow. | Prune low-priority context; summarize safely; block if evidence lost. | Improve retrieval selection and context compiler policy. |

Budget values should be deployment-profile specific. A toy workflow, enterprise analysis route, and regulated high-impact action should not share the same hard-coded token, cost, turn, or tool-call ceiling.

## **User Communication Matrix**

AI incident communication must be truthful about state, uncertainty, user impact, and safe next actions. Do not say “the AI hallucinated” as if the platform were a haunted toaster. Say what failed, what is saved, what is blocked, what is known, what remains unknown, and what the user can safely do.

```text
COMMUNICATION RULE

Never claim:
  - an action succeeded before verification,
  - no data was exposed before scope analysis,
  - a cache/index/model is clean before validation,
  - a degraded route is equivalent when it is not.

Communicate:
  known status, preserved state, active limitation,
  user action required, and next update path.
```

| Incident Class | Audience | What to Say | What Not to Say | User / Customer Action |
| :---- | :---- | :---- | :---- | :---- |
| **RAG Poisoning / Retrieval Quarantine** | Affected workspace users or admins. | “We detected an anomaly in part of your document retrieval index and isolated the affected sources. Search may be incomplete while verification runs.” | “All results are safe” before validation completes. | None unless asked to review quarantined documents. |
| **Model Route Degradation** | Active users on affected route. | “The primary reasoning route is temporarily unavailable. We can continue in a reduced mode with limitations, or wait for full capability.” | “Equivalent quality” if capability, citation depth, latency, or tools changed. | Choose reduced mode, wait, or save progress. |
| **State-Changing Tool Timeout** | Specific initiator / admin. | “We could not verify the action status. To prevent duplicate effects, we paused retries and saved the request for verification.” | “It failed” or “It succeeded” before source-of-record reconciliation. | Review status or wait for verification. |
| **Cross-Tenant / Privacy Investigation** | Security/admin contacts and affected users as policy requires. | “We identified a possible isolation issue and have contained the affected scope. Investigation and verification are ongoing.” | “No unauthorized access occurred” before confirmed. | Reauthenticate or rotate credentials if instructed. |
| **Prompt Injection / Security Containment** | Affected session user/admin. | “This session was paused because a security boundary was triggered. Your progress is saved, and unsafe automation is disabled.” | Revealing detection logic, system prompts, or exploit details. | Resume after review or start a clean session. |
| **Cost / Quota Halt** | User or tenant admin. | “This workflow reached its configured budget or loop limit. Progress is saved, and further automated execution is paused.” | “The system crashed” if the stop was intentional containment. | Approve more budget, simplify task, or resume manually. |
| **Parser / Citation Degradation** | User relying on documents. | “We could not verify the document layout/citation coordinates. We can provide text-only or partial results with limitations.” | Pretending visual/table evidence was inspected when it was not. | Upload cleaner file, accept text-only mode, or request review. |
| **Fail-Closed Security Block** | Affected users / status page if broad. | “We temporarily blocked this capability to preserve security and data integrity. Saved state is preserved where possible.” | “Scheduled maintenance” if the event is an active incident requiring transparency. | Wait for recovery path or contact support. |

## **Incident Review and Postmortem Model**

An AI postmortem must look beyond traditional server uptime metrics, conducting a thorough analysis of prompt templates, retrieved evidence chunks, and model configurations.20

```
  ┌────────────────────────────────────────────────────────┐  
  │                 AI POSTMORTEM SCHEMA                   │  
  ├────────────────────────────────────────────────────────┤  
  │  - Incident Summary: Impact, Core Failing Layer        │  
  │  - Root Cause: Data vs. Prompt vs. Weight Drift       │  
  │  - Chronology: Trace-linked Ingestion to Failure Path │  
  │  - Technical Evidence: Rendered Prompts & Raw Outputs │  
  │  - Evaluation Gaps: Missed Canary or Golden Sets      │  
  │  - Action Items: Preventative CI/CD Gates Added       │  
  └────────────────────────────────────────────────────────┘
```

The postmortem process is structured to systematically catalog failure metrics, trace the chronological progression, and implement permanent behavioral guards:

* **Incident Summary & Failing Layer:** Captures the severity level, blast radius, total duration, and affected tenant UUIDs, isolating the failure to its specific taxonomic class.2  
* **Root Cause & Contributing Factors:** Analyzes whether the failure originated from data drift, prompt instruction decay, or provider-side weight updates.2  
* **Trace-Linked Chronology:** Details the exact timeline of events, linking key milestones (anomaly detection, containment trigger, rollback execution) to specific OpenTelemetry trace and span IDs.1  
* **Technical Evidence Repository:** Attaches the rendered prompt string, the retrieved context chunks, and the raw generated output tokens directly to the postmortem file, enabling exact reproduction.20  
* **Evaluation & Telemetry Gaps:** Highlights why the failure escaped containment, identifying missing canary prompts or gaps in the CI/CD evaluation harness.1  
* **Permanent Improvements List:** Replaces vague "be more careful" actions with concrete, dated, and testable improvements.2 Every postmortem must commit at least one new golden test case to the regression set and one new alert threshold to Prometheus.1

## **Runbook Library**

The platform maintains a runbook library for recurring AI incident classes. Each runbook must identify the trigger, severity assumptions, first actions, containment controls, evidence to preserve, owner roles, recovery path, validation steps, communication path, and incident-to-eval follow-through.

Runbooks should not instruct responders to paste raw prompts, secrets, transaction details, or tenant data into ordinary incident tickets. Sensitive payloads belong in controlled forensic storage with secure references, access logs, and retention policy.

```text
AI OPERATIONS RUNBOOK LIBRARY

[ Incident Trigger ]
        |
        v
[ Classify ]
  semantic | retrieval | prompt | model | tool | cost | privacy | UX/review
        |
        v
[ Preserve Evidence Manifest ]
  trace IDs | hashes | secure refs | configs | state versions
        |
        v
[ Contain ]
  flag | kill switch | quarantine | route pin | credential revoke
        |
        v
[ Recover ]
  rollback | compensate | reconcile | rebuild | degrade | escalate
        |
        v
[ Validate ]
  canary | regression | policy | isolation | source-of-record check
        |
        v
[ Communicate ]
  known status | unknowns | saved state | user action | next update path
        |
        v
[ Promote Incident to Eval / Runbook Update ]
```

### **Runbook 1: Ungrounded Answer Incident (Factual Hallucination)**

* **Incident Trigger & Severity:** Automated NLI grounding checks detect a business_rule_error on an active session; nli_grounding_score falls below 0.70 over a 5-minute rolling window. SEV-2 (Contained Semantic Failure).1  
* **First 5 Minutes Actions:**  
  1. Trace the session ID to locate the active retrieval spans and the model endpoint version.1  
  2. Capture the rendered prompt string, the retrieved context chunks, and the raw output tokens.20  
  3. Toggle the FF_CACHE_BYPASS flag for the affected workspace, forcing live database lookups and bypassing potentially corrupted caches.3  
* **Containment Steps:** Force-disable advanced rag-generation routes for the tenant. Set the active trust-calibration interface to Level 3 (Inline Caveat), rendering visible uncertainty indicators for unsupported or unverified claims to communicate uncertainty.3  
* **Evidence to Preserve:** Snapshot the current vector index state, export the retrieved chunk text strings, and write the complete telemetry trace payload to the forensic directory.1  
* **Owner Roles:** SRE/Platform Lead (Primary investigator); Retrieval Owner (Context validator); Prompt Owner (Hotfix engineer).17  
* **Rollback Steps:** Revert the retrieval query rewriting template inside the prompt registry to the preceding stable commit.2  
* **Validation Steps:** Execute a parallel 50-case grounding evaluation run in staging, asserting that the model's factual outputs align with the reference documents.1  
* **Communication Path:** Render an inline caveat badge: *"I can answer conceptually, but my live retrieval database is currently optimizing. I cannot verify specific policy changes."*.3  
* **Postmortem Actions:** Convert the hallucinated query-response pair into a permanent, version-controlled golden test case inside the CI/CD pipeline to prevent future regressions.1

### **Runbook 2: Citation Failure Incident**

* **Incident Trigger & Severity:** UI monitors detect a citation_alignment_score falling below 0.75, indicating that bracketed citation markers do not map to verified coordinates inside the source documents. SEV-3 (Degraded Quality).1  
* **First 5 Minutes Actions:**  
  1. Scan the document parsing logs to check for layout-aware parsing exceptions or OCR failures.1  
  2. Verify that page coordinates exist inside the retrieved metadata schemas.1  
  3. Route document parsing tasks to the backup heuristic text parser.3  
* **Containment Steps:** Temporarily hide visual coordinate highlights on the user interface, falling back to displaying plain-text document titles.3  
* **Evidence to Preserve:** Snapshot the failing document file, the extracted DocTags markup, and the page coordinate array.21  
* **Owner Roles:** Layout & Document Engineer (Primary investigator); SRE/Platform Lead (Inference monitor).17  
* **Rollback Steps:** Revert the document parsing Docker container to the preceding stable image version.2  
* **Validation Steps:** Run an automated unit test suite, executing a coordinate-level IoU check over table extraction targets.1  
* **Communication Path:** Display a subtle UI warning card: *"Complex page layout unreadable. Using text-only reference mode."*.3  
* **Postmortem Actions:** Update the parser's configuration schema to enforce profile-appropriate rasterization and layout-extraction settings for scanned PDFs.21

### **Runbook 3: Prompt Injection Incident (Safety Breach)**

* **Incident Trigger & Severity:** Input Prompt Shields log an adversarial bypass attempt; policy_violation_rate spikes. SEV-1 (High-Impact Active Harm).1  
* **First 5 Minutes Actions:**  
  1. Isolate and freeze the active user session; block the associated IP address.2  
  2. Terminate active WebSocket connections and close active runner processes.2  
  3. Scan execution logs to identify if the model attempted to leak system instructions or execute unauthorized tools.2  
* **Containment Steps:** Revoke the session's active OAuth tokens. Route the tenant's queries to the quarantined fallback model instance.2  
* **Evidence to Preserve:** Preserve hashes and secure forensic references for the input, rendered prompt, injected payload, and tool trace history. Store raw sensitive payloads only in the controlled forensic vault.1  
* **Owner Roles:** Security Lead (Primary investigator); Prompt Owner (Defensive engineer).17  
* **Rollback Steps:** Revert the system prompt template to the last safe version in Git.3  
* **Validation Steps:** Run the purple-team jailbreak evaluation suite inside the CI/CD pipeline, verifying that the incident payload and representative variants are blocked or safely contained according to the applicable risk profile.1  
* **Communication Path:** Render a full-screen red error overlay: *"Session locked due to a security policy violation. Your progress has been saved securely."*.3  
* **Postmortem Actions:** promote the sanitized payload pattern into the adversarial evaluation suite and review whether detector training data should be updated.2

### **Runbook 4: Tool Misfire Incident (Unauthorized Action)**

* **Incident Trigger & Severity:** The database monitor alerts on an un-idempotent write action executed without active maker-checker clearance.2 SEV-1 (High-Impact Active Harm).2  
* **First 5 Minutes Actions:**  
  1. Trigger the FF_TOOL_REVOKE kill switch, disabling the misfiring API connection instantly.2  
  2. Suspend the active multi-agent loop orchestrator.2  
  3. Verify the ledger status inside the database of record to identify if writes were committed.2  
* **Containment Steps:** Revoke the tool's scoped credentials in Secrets Manager.2  
* **Evidence to Preserve:** Seal the tool call arguments, the pre-action database state hash, the idempotency key, and the Saga execution trail.1  
* **Owner Roles:** Tool Owner (Primary investigator); Saga Coordinator (Ledger checker); Compliance Lead (Risk auditor).17  
* **Rollback Steps:** Execute the registered Saga compensation payload to semantically reverse committed actions.3  
* **Validation Steps:** Run a dry-run test transaction in staging, asserting that the tool gateway rejects un-idempotent payloads.3  
* **Communication Path:** Display a full-screen modal: *"We are verifying your transaction status with the bank. Do not click buy again."*.3  
* **Postmortem Actions:** Update tool contracts to enforce physical argument validation schemas (Pydantic validation) before execution.2

### **Runbook 5: Cost Bomb Incident (Runaway Loops)**

* **Incident Trigger & Severity:** Budget monitors alert on a session crossing the 5.00 USD spend ceiling; token burn velocity spikes.1 SEV-1 (High-Impact Active Harm).2  
* **First 5 Minutes Actions:**  
  1. Force terminate the active agent execution thread.2  
  2. Revoke the session's active API routing keys inside the gateway proxy.2  
  3. Clear the active memory cache for the running conversation.2  
* **Containment Steps:** Apply a zero-token budget constraint to the tenant's workspace configurations.2  
* **Evidence to Preserve:** Record the cumulative token metrics, the execution turn count, the planning trace, and the exact formatting errors.1  
* **Owner Roles:** SRE/Platform Lead (Resource auditor); Agent Orchestration Lead (Loop debugger).17  
* **Rollback Steps:** Invalidate active model prompt caches for the affected templates.2  
* **Validation Steps:** Execute a loop simulation test in staging to verify that the orchestrator terminates tasks when thresholds are breached.1  
* **Communication Path:** Display an inline alert card: *"Session paused. You've reached your workspace's token limit. Progress saved."*.3  
* **Postmortem Actions:** Refactor prompt templates to reduce tool-schema overhead; implement hard limits on planning iterations.2

### **Runbook 6: Model Drift Incident (Behavior Regression)**

* **Incident Trigger & Severity:** Strategic telemetry logs a cosine distance shift > 0.15 compared to reference embeddings.1 SEV-2 (Contained Semantic Failure).2  
* **First 5 Minutes Actions:**  
  1. Scan vLLM prometheus metrics to check for changes in latency, throughput, or perplexity.1  
  2. Run the 100-case canary prompt suite in parallel.1  
  3. Freeze all active prompt or routing configurations in staging.30  
* **Containment Steps:** Re-route production traffic from the drifted endpoint to the preceding stable model snapshot.3  
* **Evidence to Preserve:** Save the generated output tokens, the calculated centroid distances, and the canary performance logs.1  
* **Owner Roles:** Model Owner (Lead investigator); AI Operations Lead (Gateway controller); SRE Lead.17  
* **Rollback Steps:** Revert the active model endpoint route inside the gateway proxy.20  
* **Validation Steps:** Execute the full CI/CD regression evaluation suite, asserting that accuracy scores meet baseline thresholds.1  
* **Communication Path:** Subtle header notification: *"Running in efficient compatibility mode to optimize system accuracy."*.3  
* **Postmortem Actions:** Establish automated daily embedding drift checks inside production telemetry collections.1

### **Runbook 7: Corpus Poisoning Incident**

* **Incident Trigger & Severity:** HubScan flags a document vector with a robust z-score > 5.0, indicating topological index poisoning.2 SEV-1 (High-Impact Active Harm).2  
* **First 5 Minutes Actions:**  
  1. Apply a Row-Level Security database constraint to filter out the poisoned document IDs from active search.2  
  2. Suspend the indexing worker's document ingestion pipeline.2  
  3. Quarantine the poisoned files inside an offline S3 bucket.2  
* **Containment Steps:** Disable vector search queries for the affected tenant workspace; fall back to BM25 keyword matching.3  
* **Evidence to Preserve:** Preserve source IDs, source version hashes, chunk/vector IDs, secure evidence references, embedding metadata, and robust z-score logs.1  
* **Owner Roles:** Retrieval Owner (Primary investigator); Database Administrator (Index controller); Security Lead.17  
* **Rollback Steps:** Rebuild the vector database HNSW graph from the last safe backup.2  
* **Validation Steps:** Re-run vector query simulations, asserting that retrieval returns clean nearest neighbors.1  
* **Communication Path:** Status banner: *"Search capabilities are operating in cached mode. Real-time updates may be delayed."*.3  
* **Postmortem Actions:** Enforce cryptographic signature checks (Sigstore/C2PA) on all files before database ingestion.2

### **Runbook 8: Human Review Queue Failure**

* **Incident Trigger & Severity:** Reviewer alerts trigger on queue backlog limits; average approval times fall below 350 ms.1 SEV-2 (Contained Semantic Failure).2  
* **First 5 Minutes Actions:**  
  1. Halt high-volume automated routing pipelines.2  
  2. Switch active workspaces to safe default states, blocking mutations without reviewer signatures.2  
  3. Route priority reviews to the backup supervisor queue.3  
* **Containment Steps:** Temporarily lock high-risk tool execution gates.2  
* **Evidence to Preserve:** Log the queue backlog stats, reviewer dwell times, and unapproved draft files.1  
* **Owner Roles:** Support Lead (Queue coordinator); Compliance Lead (Operations auditor).17  
* **Rollback Steps:** Revert approval workflow configurations to the last verified checklist.3  
* **Validation Steps:** Run gold-label sentinel check cases through the queue to audit reviewer alignment.1  
* **Communication Path:** Warning card: *"Verification queues are temporarily delayed. High-risk transactions may take up to 2 hours."*.3  
* **Postmortem Actions:** Establish automated limits on the number of cases routed to individual reviewers per hour.2

### **Runbook 9: Degraded-Mode Fail-Open Anomaly**

* **Trigger Scenario:** A gateway routing failure allows a query to bypass active security filters or formatting validation gates.2 SEV-0 (Catastrophic System Failure).2  
* **First 5 Minutes Actions:**  
  1. Activate the global platform kill switch, freezing user interactions.2  
  2. Invalidate the gateway's active API routing configurations.1  
  3. Check log files to identify if unredacted data or unsafe commands crossed the interface.1  
* **Containment Steps:** Suspend all active model connections. Enforce a hard fail-closed configuration across all edge proxies.2  
* **Evidence to Preserve:** Copy the raw gateway configurations, the W3C tracecontext context logs, and the blocked output streams.1  
* **Owner Roles:** SRE/Platform Lead (Primary investigator); AI Operations Lead (Gateway controller); Security Lead.17  
* **Rollback Steps:** Rebuild and deploy the gateway proxy using the last stable Docker container image.3  
* **Validation Steps:** Execute the full CI/CD security and isolation test suite, confirming 100% block rates.1  
* **Communication Path:** Public status page update: *"The platform is offline for scheduled security system maintenance. All user data is secured."*.3  
* **Postmortem Actions:** Consolidate all retry, fallback, and validation rules inside a centralized, self-hosted API gateway.3

### **Runbook 10: Privacy and Cross-Tenant Leak Incident**

* **Trigger Scenario:** Session analyzers detect a tenant ID mismatch between a user's JWT and the retrieved metadata schemas.2 SEV-0 (Catastrophic System Failure).2  
* **First 5 Minutes Actions:**  
  1. Isolate the affected tenant namespaces inside the pgvector and Redis clusters.2  
  2. Revoke active session tokens and terminate Websocket connection pools.2  
  3. Isolate and block access to the affected vector database index partitions.2  
* **Containment Steps:** Enforce a global read-only mode for the isolated workspaces, preventing document updates.3  
* **Evidence to Preserve:** Record the trace IDs, the mismatched user identities, the retrieved vector coordinates, and the cache keys.1  
* **Owner Roles:** SRE/Platform Lead (Primary investigator); AI Operations Lead (Gateway controller); Privacy Lead; Security Lead.17  
* **Rollback Steps:** Flush all cached prompt-response vectors and re-initialize isolated cache spaces.2  
* **Validation Steps:** Execute 1,000 automated isolation probe queries inside staging, verifying that representative isolation probes cannot retrieve cross-tenant resources under the affected configurations.2  
* **Communication Path:** Dedicated enterprise customer notification: *"We have isolated a brief namespace configuration overlap in your workspace. Active session credentials have been updated to preserve your privacy."*.3  
* **Postmortem Actions:** Enforce database-level Row-Level Security (RLS) policies on every vector similarity query.2

## **Operational Readiness and Game Days**

Before launching an AI system, teams must prove that feature flags, kill switches, rollback paths, evidence capture, runbooks, on-call roles, customer communication templates, and evaluation feedback loops operate correctly under pressure.18 Operational readiness is verified through a structured, multi-step game day:

  Fault Injection ──► Telemetry Trigger ──► Runbook Activation ──► Forensics Check ──► Verification

### **Readiness scenarios executed in staging environments:**

1. **Prompt Injection and Exfiltration:** A simulated malicious user attempts to bypass system prompt safety blocks and exfiltrate customer account details.2 The game day tests the speed of the ARGUS output filter and verifies that the system isolates the compromised session in under 120 milliseconds.2  
2. **Vector Index Topological Poisoning:** Responders inject 5 adversarially crafted documents into the corporate knowledge base.31 The exercise verifies that the HubScan detector successfully flags and quarantines the poisoned vector coordinates, and that the retrieval engine falls back to lexical matches.2  
3. **Model Version Behavior Regression:** The team simulates an unannounced model provider update that alters JSON formatting.2 Responders must verify that the gateway proxy detects the regression, logs the routing decision, and executes an atomic rollback to the stable model checkpoint in under 60 seconds.1  
4. **Runaway Agent Loop and Billing Spike:** Responders run an agent configuration designed to repeat identical database lookups indefinitely.2 The game day verifies that the budget gateway terminates the loop execution path, triggers a fail-closed status, and preserves the failing traces.1

**Deployment Readiness Checklist:**

* [ ] Global and tenant-scoped kill switches are verified and accessible to on-call SREs.2  
* [ ] The gateway proxy supports atomic endpoint re-routing without requiring code redeployments.20  
* [ ] The pgvector database enforces PostgreSQL Row-Level Security (RLS) on all search transactions.2  
* [ ] Ingestion pipelines are configured with strict magic-byte scanning and run within microVM sandboxes.2  
* [ ] The telemetry collector redact pipeline masks PII and API keys from central logs.1  
* [ ] Every system prompt template is version-controlled and tied to an automated regression gate.1

## **Incident-to-Eval Feedback Loop**

Every significant AI incident must create or update evals, telemetry, artifacts, policies, runbooks, or documented exceptions. This feedback loop is the platform's immunological learning cycle:

  [Production Failure] ──► Trace Captured ──► Sanitized via ARGUS   
                                                   │  
                                                   ▼  
  ◄── Golden Case Promoted ◄── SME Review 

The feedback loop is executed through a disciplined engineering pipeline:

1. **Incident Discovery:** High-severity incidents, user-initiated corrections, citation mismatches, tool timeouts, and human approval overrides are automatically captured by the strategic telemetry layer.1  
2. **Telemetry Redaction:** To protect sensitive data and preserve compliance (e.g., GDPR, HIPAA), the raw trace is passed through the inline ARGUS scanning gate, replacing PII, system passwords, and API keys with secure placeholders.1  
3. **Ground Truth Authoring:** The sanitized trace is packaged into a standard golden case format, and subject matter experts assign the correct ground-truth typologies and rubrics to resolve the failure.1  
4. **Golden Set Promotion:** The new case is run against the current production baseline and committed to the versioned evaluation repository, transforming the production incident into an automated release gate to prevent regressions.1

## **Cross-Canon Handoff Map**

AI-ENG-AC defines the operational response layer for the canon: detection, intake, triage, containment, rollback, communication, incident review, and incident-to-eval promotion. It consumes telemetry, evaluation, verification, security, degraded-mode, and governance artifacts, then feeds improvements back into the lifecycle.

| Canon Report | Handoff Into AC | AC Operational Use | Feedback Returned |
| :---- | :---- | :---- | :---- |
| **AI-ENG-B — Context Architecture** | Context object IDs, memory state, session scope, compaction records. | Diagnose context loss, stale memory, state corruption, or instruction decay. | Incident-derived context invariants and state-preservation tests. |
| **AI-ENG-D — Corpus Engineering** | Source authority, corpus lifecycle state, provenance, ownership, document version. | Quarantine suspect sources and scope data/corpus incidents. | New corpus validation, lifecycle, and provenance requirements. |
| **AI-ENG-E — Retrieval Pipeline** | Retrieval traces, candidate sets, filters, citation bundles, evidence packets. | Diagnose grounding, citation, and retrieval failure incidents. | New retrieval evals, filter checks, and evidence-sufficiency gates. |
| **AI-ENG-F — Freshness and Conflict Detection** | Freshness status, conflict packets, source version drift, citation stability. | Determine whether stale or conflicting evidence caused user-visible harm. | Freshness alerts and conflict-resolution runbook updates. |
| **AI-ENG-L — Serving Architecture** | Route manifests, latency, queue state, model endpoints, cache behavior. | Execute route rollback, failover, capacity containment, and serving recovery. | New route SLOs, rollback drills, and serving canaries. |
| **AI-ENG-M — Agentic Orchestration** | Workflow state, loop counters, no-progress hashes, task graph. | Stop runaway agents, preserve plan state, and diagnose orchestration failures. | New loop limits, state checkpoints, and agent termination tests. |
| **AI-ENG-N — Tool Contracts** | Tool schemas, manifests, argument validators, side-effect classes. | Disable unsafe tools and diagnose tool payload or schema failures. | Contract hardening, idempotency requirements, and new tool evals. |
| **AI-ENG-O — Action Verification** | Action ledgers, pre/post state hashes, idempotency keys, verification state. | Reconcile unknown tool state, compensate committed effects, prevent false success. | New verification predicates and state-reconciliation tests. |
| **AI-ENG-P — Multimodal Understanding** | Parser versions, evidence coordinates, OCR/layout confidence, media refs. | Diagnose parser, OCR, document, chart, image, and video evidence incidents. | Parser regression cases and evidence-adequacy thresholds. |
| **AI-ENG-Q — Speech / Realtime** | Transcript state, endpointing, confirmation, interruption, voice degradation events. | Pause high-impact voice workflows and switch to safer confirmation modes. | New noisy-audio, confirmation, and barge-in game-day tests. |
| **AI-ENG-R — UI Agents** | Browser traces, DOM/screenshot hashes, action verification, automation pause state. | Diagnose blind clicks, UI drift, false completion, and interface trust failures. | UI-agent recovery and action-verification tests. |
| **AI-ENG-S — Production Pathologies** | Failure classes, malformed output, hallucination subtypes, brittle-chain patterns. | Classify semantic incidents and choose containment/recovery path. | New pathology-specific runbooks and regression gates. |
| **AI-ENG-T — Boundary Defense** | Tenant scope, authority hierarchy, RLS state, cache isolation, injection events. | Contain prompt injection, cross-tenant leakage, and boundary violations. | New isolation probes and boundary-defense incident cases. |
| **AI-ENG-U — Supply Chain Security** | Artifact signatures, dependency manifests, sandbox profiles, model/data provenance. | Quarantine unsafe artifacts and verify rollback targets. | New artifact-readiness and loader-hardening requirements. |
| **AI-ENG-V — Resource Abuse** | Budget ceilings, token burn, tool-call limits, retry storms, abuse signals. | Halt cost bombs, throttle workflows, and enforce fail-closed budget controls. | New resource-abuse drills and budget-policy changes. |
| **AI-ENG-W — UX Resilience** | Degraded-mode states, fallback contracts, continuity state, user disclosure events. | Communicate degraded states and preserve user progress during incidents. | New degraded-mode tests and disclosure templates. |
| **AI-ENG-X — User Trust** | Trust calibration signals, citation interactions, user corrections, contestability events. | Detect user-facing trust failures and repair transparency patterns. | New disclosure, evidence, and contestability requirements. |
| **AI-ENG-Y — Human Review** | Approval records, reviewer queue state, maker-checker outcomes, escalation packages. | Pause unsafe automation and route high-impact uncertainty to humans. | New reviewer sentinel cases and approval-flow thresholds. |
| **AI-ENG-Z — Strategic Telemetry** | Trace IDs, spans, token/cost metrics, routing events, redaction metadata. | Intake, scope, replay, and correlate incidents. | New telemetry fields, alerts, dashboards, and SLOs. |
| **AI-ENG-AA — Evaluations** | Golden sets, canaries, regression suites, calibrated scoring artifacts. | Validate rollback, hotfix, mitigation, and closure. | Incident traces promoted into permanent eval cases. |
| **AI-ENG-AB — Verification Artifacts** | Audit trails, secure references, trace manifests, policy/model/tool versions. | Preserve forensic record and support reproducible postmortems. | New evidence-package requirements and replay constraints. |
| **AI-ENG-AD — Governance** | Policy ownership, approval workflows, reporting obligations, accountability boundaries. | Determine reporting, escalation, exception, and lifecycle-governance requirements. | Postmortem action items, governance exceptions, and policy updates. |
| **AI-ENG-AJ — Reference Architectures** | Deployment blueprints, gateway patterns, sandboxing, audit stores, runbook automation. | Implement operational controls as reference architecture components. | Architecture updates based on incidents and game days. |

## **Strategic Conclusions and Architectural Recommendations**

To transition from ad-hoc troubleshooting to systemic, high-assurance behavioral governance, enterprise platforms must consolidate their operational procedures outside the model's cognitive boundary.1 Based on the analyses compiled in this report, the following four strategic principles are recommended for deployment architectures:

1. **Enforce State Verification Before Confirmations:** Never allow conversational or auditory interfaces to generate verbal completion claims (e.g., "Your payment has been sent") until the underlying API transaction has been committed and verified inside the database of record.2 Spoken or generated claims must never outrun physical reality.2  
2. **Centralize Resilience at the Gateway Layer:** Avoid writing separate retry, fallback, and rate-limiting logic inside individual application services.3 Centralize these capabilities within a high-performance, budget-aware runtime gateway positioned entirely outside the model's cognitive boundary, ensuring consistent policy enforcement, cost tracking, and provider failovers across the entire organization.1  
3. **Secure Caches against Timing Side-Channels:** Sharing semantic or prefix caches globally across mutually untrusted tenants introduces timing side-channel risks.3 All cache keys must be cryptographically bound to tenant identity and user permissions, and serving runtimes must deploy selective prefix isolation (such as the CacheSolidarity framework) to prevent timing side-channel probes from exfiltrating private context.2  
4. **Enforce Strict Least-Privilege Tool Credentials:** Model-driven agents must never run with broad administrative service tokens or "god-mode" database accounts.2 Every tool execution must be mediated by a secure credential broker that validates user identity and mints short-lived, highly restricted OAuth tokens (validity less than 900 seconds) specifically for that single execution, protecting local file systems and egress routes from lateral compromise.2

## **Durable Principles of AI Operations**

1. **Service Recovery Is Not Behavioral Recovery**  
   A system is not recovered because the endpoint is online. It is recovered when outputs, actions, evidence, routing, policy, and user-facing status are back inside the approved behavioral envelope.

2. **Contain Harm Before Solving the Mystery**  
   Incident response begins with stopping active damage. Root cause can wait; unauthorized tools, poisoned indexes, bad routes, and leaking caches cannot.

3. **Preserve Evidence Before Destructive Cleanup**  
   Cache flushes, redeploys, session wipes, and credential rotations can destroy forensic state. Preserve hashes, traces, manifests, and secure references first when safety allows.

4. **Rollback the Smallest Effective Surface**  
   Do not revert the whole platform when a prompt, adapter, cache namespace, corpus lifecycle state, or tool contract is the failing surface.

5. **Unknown State Is a First-Class Incident State**  
   Timeouts and partial commits are not success and not failure. They require hold, reconciliation, compensation, forward recovery, or escalation.

6. **Prompt Hotfixes Are Temporary Operational Controls**  
   Emergency prompt changes must be versioned, bounded, tested, owned, and either promoted through normal release gates or retired.

7. **Runbooks Must Be Executable Under Stress**  
   A runbook is not a philosophy pamphlet. It should say who acts, what they disable, what they preserve, what they validate, and how they communicate.

8. **Communications Must Respect Evidence State**  
   Never reassure users that no data was exposed, no action occurred, or no harm happened until verification supports it.

9. **Every Significant Incident Becomes an Evaluation**  
   Production failures should harden the system. Sanitized incident traces must become golden cases, adversarial tests, telemetry alerts, or governance controls.

10. **Operations Belongs Outside the Model Boundary**  
   Kill switches, feature flags, credential revocation, route control, policy enforcement, and rollback must be deterministic controls, not polite requests embedded in prompts.

#### **Works cited**

1. [KNOWLEDGE] - AI Engineering - Volume 9. Z-AB Observability, Evaluation, and Verification  
2. [KNOWLEDGE] - AI Engineering - Volume 7. S-V Failure, Security, and Hostile Environments  
3. [KNOWLEDGE] - AI Engineering - Volume 8. W-Y Resilience, Degraded Modes, and Human Trust  
4. Incident management | AI Governance Platform - VerifyWise, accessed June 12, 2026, [https://verifywise.ai/platform/incident-management](https://verifywise.ai/platform/incident-management)  
5. Preventing Repeated Real World AI Failures by Cataloging Incidents: The AI Incident Database - AAAI, accessed June 12, 2026, [https://cdn.aaai.org/ojs/17817/17817-13-21311-1-2-20210518.pdf](https://cdn.aaai.org/ojs/17817/17817-13-21311-1-2-20210518.pdf)  
6. Resilience Circuit Breakers for Agentic AI - Medium, accessed June 12, 2026, [https://medium.com/@michael.hannecke/resilience-circuit-breakers-for-agentic-ai-cc7075101486](https://medium.com/@michael.hannecke/resilience-circuit-breakers-for-agentic-ai-cc7075101486)  
7. MLSecOps Enterprise Guide 2026: Securing AI/ML Pipelines | BeyondScale, accessed June 12, 2026, [https://beyondscale.tech/blog/mlsecops-enterprise-guide-2026](https://beyondscale.tech/blog/mlsecops-enterprise-guide-2026)  
8. Model Rollback: Reverting a Deployed Model to a Previous Version When Problems Occur, accessed June 12, 2026, [https://www.sandgarden.com/learn/model-rollback](https://www.sandgarden.com/learn/model-rollback)  
9. Strengthening Emergency Preparedness and Response for AI Loss of Control Incidents - RAND, accessed June 12, 2026, [https://www.rand.org/content/dam/rand/pubs/research_reports/RRA3800/RRA3847-1/RAND_RRA3847-1.pdf](https://www.rand.org/content/dam/rand/pubs/research_reports/RRA3800/RRA3847-1/RAND_RRA3847-1.pdf)  
10. LLMOps Pipeline Architecture Explained Simply | LaikaTest, accessed June 12, 2026, [https://laikatest.com/blogs/llmops-pipeline-architecture](https://laikatest.com/blogs/llmops-pipeline-architecture)  
11. AI SRE explained: what it is, how it works, and the human vs. AI reality | Blog - Incident.io, accessed June 12, 2026, [https://incident.io/blog/what-is-ai-sre-complete-guide-2026](https://incident.io/blog/what-is-ai-sre-complete-guide-2026)  
12. AI-Powered Incident Response: Use Cases, Frameworks, Tools, and a Complete Implementation Playbook - UnderDefense, accessed June 12, 2026, [https://underdefense.com/blog/ai-incident-response/](https://underdefense.com/blog/ai-incident-response/)  
13. Incident Priority - PagerDuty Knowledge Base, accessed June 12, 2026, [https://support.pagerduty.com/main/docs/incident-priority](https://support.pagerduty.com/main/docs/incident-priority)  
14. Incident Severity Levels Fully Explained Plus How-To's and Best Practices - Giva, accessed June 12, 2026, [https://www.givainc.com/blog/incident-severity-levels/](https://www.givainc.com/blog/incident-severity-levels/)  
15. How to Build Incident Severity Definitions - OneUptime, accessed June 12, 2026, [https://oneuptime.com/blog/post/2026-01-30-incident-severity-definitions/view](https://oneuptime.com/blog/post/2026-01-30-incident-severity-definitions/view)  
16. Prompt Injection Attacks: The LLM Security Risk IT Leaders Must Address, accessed June 12, 2026, [https://biztechmagazine.com/article/2026/04/prompt-injection-attacks-llm-security-risk-it-leaders-must-address-perfcon](https://biztechmagazine.com/article/2026/04/prompt-injection-attacks-llm-security-risk-it-leaders-must-address-perfcon)  
17. How to Implement Incident Response Procedures, accessed June 12, 2026, [https://oneuptime.com/blog/post/2026-01-30-sre-incident-response-procedures/view](https://oneuptime.com/blog/post/2026-01-30-sre-incident-response-procedures/view)  
18. LLMOps: Driving Strategic and Effective AI Lifecycle Management - Nitor Infotech, accessed June 12, 2026, [https://www.nitorinfotech.com/blog/llmops-driving-strategic-and-effective-ai-lifecycle-management/](https://www.nitorinfotech.com/blog/llmops-driving-strategic-and-effective-ai-lifecycle-management/)  
19. What is the Incident Response Process in SRE? - Visualpath, accessed June 12, 2026, [https://visualpathblogs.com/site-reliability-engineering/what-is-the-incident-response-process-in-sre/](https://visualpathblogs.com/site-reliability-engineering/what-is-the-incident-response-process-in-sre/)  
20. The AI Incident Response Playbook: Diagnosing LLM Degradation in Production, accessed June 12, 2026, [https://tianpan.co/blog/2026-04-19-ai-incident-response-playbook-llm-production](https://tianpan.co/blog/2026-04-19-ai-incident-response-playbook-llm-production)  
21. [KNOWLEDGE] - AI Engineering - Volume 6. P-R Multimodal and Interface-Controlling Systems  
22. Defending AI Systems: A New Framework for Incident Response in the Age of Intelligent Technology - Coalition for Secure AI, accessed June 12, 2026, [https://www.coalitionforsecureai.org/defending-ai-systems-a-new-framework-for-incident-response-in-the-age-of-intelligent-technology/](https://www.coalitionforsecureai.org/defending-ai-systems-a-new-framework-for-incident-response-in-the-age-of-intelligent-technology/)  
23. SRE Incident Management Best Practices Every Startup Needs - Rootly, accessed June 12, 2026, [https://rootly.com/sre/sre-incident-management-best-practices-startup-needs-04bdd](https://rootly.com/sre/sre-incident-management-best-practices-startup-needs-04bdd)  
24. Kubernetes Deployment Automation: A Complete Guide - Plural.sh, accessed June 12, 2026, [https://www.plural.sh/blog/kubernetes-deployment-automation-guide/](https://www.plural.sh/blog/kubernetes-deployment-automation-guide/)  
25. What is JML? Meaning, Architecture, Examples, Use Cases, and How to Measure It (2026 Guide) - DevSecOps School, accessed June 12, 2026, [https://devsecopsschool.com/blog/jml/](https://devsecopsschool.com/blog/jml/)  
26. LLM Operations Architecture: Runtime Governance for Production AI Systems - Rack2Cloud, accessed June 12, 2026, [https://www.rack2cloud.com/llm-ops-model-deployment-strategy-guide/](https://www.rack2cloud.com/llm-ops-model-deployment-strategy-guide/)  
27. LLM Security: Complete Guide for CTOs and IT Security Officers - MobiDev, accessed June 12, 2026, [https://mobidev.biz/blog/llm-security-guide-for-ctos-it-security-officers](https://mobidev.biz/blog/llm-security-guide-for-ctos-it-security-officers)  
28. The Roadmap for Mastering LLMOps in 2026 - MachineLearningMastery.com, accessed June 12, 2026, [https://machinelearningmastery.com/the-roadmap-for-mastering-llmops-in-2026/](https://machinelearningmastery.com/the-roadmap-for-mastering-llmops-in-2026/)  
29. Runbook Automation Self-Hosted - PagerDuty, accessed June 12, 2026, [https://www.pagerduty.com/platform/automation/process-software/](https://www.pagerduty.com/platform/automation/process-software/)  
30. Qwen 3.6 in Production: Release Runbook, AI Rollback, and LLMOps Versioning, accessed June 12, 2026, [https://stajic.de/blog/qwen-3-6-in-production-release-runbook-ai-rollback-and-llmops-versioning](https://stajic.de/blog/qwen-3-6-in-production-release-runbook-ai-rollback-and-llmops-versioning)  
31. Prompt Injection Attacks in Large Language Models and AI Agent Systems: A Comprehensive Review of Vulnerabilities, Attack Vectors, and Defense Mechanisms - Preprints.org, accessed June 12, 2026, [https://www.preprints.org/manuscript/202511.0088?utm_source=chatgpt.com](https://www.preprints.org/manuscript/202511.0088?utm_source=chatgpt.com)

---

## Attribution

Part of **Stunspot’s Guide to AI Systems** — *The AI Engineering Systems Canon*.

Created by **Sam “stunspot” Walker** / **Collaborative Dynamics**.

Repository: https://github.com/Stunspot/stunspots-guide-to-ai-systems  
Stunspot: https://stunspot.com  
Collaborative Dynamics: https://www.collaborative-dynamics.com  
Discord: https://discord.gg/stunspot  

Licensed under **CC BY-NC-SA 4.0** unless otherwise stated.  
Commercial use, resale, paid redistribution, inclusion in commercial training products, or incorporation into paid knowledge-base products requires prior written permission.

[← Back to Canon Map](../canon-map.md)