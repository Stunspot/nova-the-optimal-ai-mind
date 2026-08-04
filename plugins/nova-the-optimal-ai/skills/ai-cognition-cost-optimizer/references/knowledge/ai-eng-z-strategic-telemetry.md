# AI-ENG-Z — Strategic Telemetry - Traces, Tokens, Latency & Semantic Drift

## **Doctrinal Foundations and the Green Dashboard Fallacy**

In high-dimensional artificial intelligence systems, production reliability cannot be measured by traditional application performance monitoring (APM) paradigms.1 In legacy web architectures, system health is treated as a binary or scalar state defined by infrastructure metrics: a service is considered healthy when APIs return successful status codes, server workloads are balanced, database connections are active, and latency remains within acceptable thresholds.2 However, when these architectures are driven by probabilistic large language models (LLMs) and multi-agent loops, backend availability does not guarantee a successful, safe, or contextually coherent user transaction.1

An artificial intelligence gateway can return a successful HTTP 200 payload that contains a complete structural schema failure, an unauthorized tool execution, a cross-tenant data leak, or an ungrounded factual confabulation.1 Conversely, a system can exhibit optimal hardware utilization and high throughput while delivering answers that silently violate safety boundaries, omit critical citations, or trap agentic loops in expensive, infinite executions.1

This mismatch establishes the **Green Dashboard Fallacy**: the erroneous belief that an AI system is healthy because conventional infrastructure metrics are green.1 In production AI engineering, a green infrastructure dashboard can coexist with a red behavioral and meaning-level system.1

Strategic telemetry is the first-class observability discipline designed to resolve this fallacy.1 It is defined as the systematic capture, correlation, protection, and interpretation of traces, spans, tokens, latency, errors, retries, retrieval events, tool calls, routing decisions, cost attribution, user trust signals, governance events, and semantic drift.1 It treats telemetry not merely as infrastructure logs, but as the primary evidence substrate required for evaluation, replay, debugging, forensic investigation, and behavioral governance.1

### **Artifact 1: Conceptual Glossary**

| Term | Technical Definition | Primary Operational Metric | Standard Production Target |
| :---- | :---- | :---- | :---- |
| **Strategic Telemetry** | The systematic capture, correlation, protection, and interpretation of semantic, economic, behavioral, security, and operational signals across an AI system’s execution path. | Behavioral Observability Coverage | Coverage is sufficient to debug, replay, evaluate, and govern high-impact workflows. |
| **AI Trace** | A structured graph representing the execution path of a probabilistic interaction across model calls, retrieval, tools, routing, policy checks, user actions, and state transitions. | Trace Completion Rate | Critical execution paths emit complete enough traces for replay and incident analysis. |
| **Span** | The atomic unit of observable work inside a trace, such as model inference, retrieval, reranking, tool execution, parsing, moderation, or human review. | Span Duration / Status Coverage | Required spans include status, timing, error class, and correlation identifiers. |
| **GenAI Semantic Convention** | A configured OpenTelemetry/OpenInference-compatible attribute vocabulary for model, provider, token, tool, retrieval, and agent telemetry. | Convention Compliance Score | Required attributes are present for the configured convention version. |
| **Token Telemetry** | Tracking of input, output, cached, embedding, reasoning, retry, repair, and wasted tokens where exposed by providers or runtime gateways. | Token Attribution Completeness | High-impact and billable usage is attributed to tenant, user/session, workflow, route, and model where applicable. |
| **Time to First Token (TTFT)** | Duration from request dispatch until the first streamed token or first response chunk is available. | TTFT by Workload Profile | TTFT remains within workload-specific SLOs. |
| **Prefill Latency** | Compute-bound latency required to process prompt/context tokens and initialize model state before generation. | Prefill P95 / P99 | Prefill latency scales within expected envelope for prompt length and model route. |
| **Decode Latency** | Memory-bandwidth-sensitive latency required to generate completion tokens sequentially. | Inter-Token Latency / TPS | Decode performance remains within model and hardware profile expectations. |
| **Routing Decision** | Runtime selection of model, provider, fallback path, cache, human review, or fail-closed route based on capability, cost, latency, safety, and availability. | Routing Decision Validity | Route satisfies task capability floor and policy constraints. |
| **Retrieval Event** | A vector, lexical, relational, hybrid, or document-expansion query performed to gather evidence for context or citation. | Retrieval Sufficiency / Fan-Out | Retrieval remains authorized, bounded, freshness-aware, and evidence-adequate. |
| **Tool Trace** | The structured record of tool selection, arguments, authorization, execution status, cost, side effects, and verification state. | Tool Verification Coverage | High-impact tool calls include pre-action authorization and post-action verification status. |
| **Cost Attribution** | Mapping of resource consumption to tenant, user, session, workflow, model, tool, retrieval, parser, batch job, or incident. | Attributed Spend Ratio | Material spend is attributable or explicitly marked unknown/pending reconciliation. |
| **Semantic Drift** | Shift in model behavior, grounding, style, refusal behavior, citation behavior, schema adherence, or policy compliance over time. | Drift Signal Ensemble | Drift is evaluated against calibrated baselines, not universal magic thresholds. |
| **Behavioral Health** | State where outputs, citations, actions, costs, safety checks, retries, routing, and user-visible behavior remain within expected envelopes. | Behavioral Incident Rate | High-impact behavioral failures trigger containment, review, or release gates. |
| **Green Dashboard Fallacy** | The diagnostic error of treating infrastructure health as sufficient evidence of AI-system health. | Hidden Failure Detection Rate | Behavioral and semantic checks supplement infrastructure metrics. |
| **Trace Redaction** | Removal, masking, hashing, or reference-only storage of sensitive payloads before telemetry reaches general observability systems. | Sensitive Payload Exposure Rate | Sensitive data exposure is blocked, minimized, or isolated through controlled references. |
| **Observability SLO** | A service objective defined over behavioral, semantic, economic, or governance metrics. | SLO Compliance by Risk Class | SLOs are calibrated per workload, risk tier, and operational route. |## **The High-Dimensional AI Trace Model**

An AI interaction must not be represented as a single, flat request-response event. It functions as an asymmetrical, stateful, multi-agent execution graph where a single user prompt can trigger parallel retrieval queries, recursive formatting repairs, multi-step tool executions, and progressive model fallbacks.1 The system must trace the entire journey as a tree of nested spans connected by parent-child relationships, preserving execution state and variables across the entire lifecycle.4

### **Artifact 2: AI Trace Model**

```text
AI TRACE MODEL

Root Span
  span.kind = AGENT
  name = "Legal Review Orchestrator"
  trace_id = "8f92a10c7d3a4e9f9a1b6c5d4e3f2010"
  span_id  = "00f067aa0ba902b7"
  parent_id = null

  attributes:
    session.hash = "sha256:session_hash"
    tenant.hash = "sha256:tenant_hash"
    workflow.id = "wf_contract_review_2026_001"
    risk_tier = "high"

  Child Span
    span.kind = CHAIN
    name = "Compile Context"
    span_id = "1a2b3c4d5e6f7081"
    parent_id = "00f067aa0ba902b7"

    Child Span
      span.kind = RETRIEVER
      name = "Authorized Document Retrieval"
      span_id = "5e6f708192a3b4c5"
      parent_id = "1a2b3c4d5e6f7081"

      attributes:
        retriever.name = "policy_document_search"
        data_source.id = "policy_corpus"
        retrieval.query_hash = "sha256:query_hash"
        retrieval.candidate_count = 12
        retrieval.authorized_candidate_count = 8

      Span Event
        name = "Document Chunk Retrieved"
        event.parent_span_id = "5e6f708192a3b4c5"
        attributes:
          document.id = "doc_xyz"
          chunk.id = "chunk_014"
          document.score = 0.98
          document.version_hash = "sha256:doc_version_hash"
          document.permission_version = "perm_v17"

    Child Span
      span.kind = LLM
      name = "Generate Audit Draft"
      span_id = "3d4e5f60718293a4"
      parent_id = "1a2b3c4d5e6f7081"

      attributes:
        gen_ai.provider.name = "provider_name"
        gen_ai.request.model = "primary_reasoning_route"
        gen_ai.response.model = "primary_reasoning_route"
        gen_ai.usage.input_tokens = 4120
        gen_ai.usage.output_tokens = 780
        gen_ai.response.finish_reasons = ["tool_calls"]

    Child Span
      span.kind = TOOL
      name = "Draft Ledger Action"
      span_id = "7a8b9c0d1e2f3041"
      parent_id = "1a2b3c4d5e6f7081"

      attributes:
        tool.name = "ledger_write"
        tool.action_class = "high_risk_mutation"
        tool.payload_hash = "sha256:payload_hash"
        tool.idempotency_key_hash = "sha256:idempotency_key_hash"
        approval.status = "PENDING"

      Span Event
        name = "Maker-Checker Initiated"
        event.parent_span_id = "7a8b9c0d1e2f3041"
        attributes:
          approval.request_id = "approval_123"
          approval.risk_tier = "HIGH"
          approval.payload_hash = "sha256:payload_hash"

  Child Span
    span.kind = GUARDRAIL
    name = "PII Leak Check"
    span_id = "9c0d1e2f30415263"
    parent_id = "00f067aa0ba902b7"

    attributes:
      guardrail.name = "output_redaction"
      guardrail.result = "pass"
      redaction.count = 0
      user_disclosure_shown = false
```

Trace examples should use opaque or hashed identifiers for tenants, users, sessions, prompts, payloads, and idempotency keys. Raw user IDs, tenant names, prompt text, credentials, and tool payloads should not be propagated as general-purpose telemetry attributes.

### **Context Propagation across Distributed Transport Channels**

To maintain trace continuity across model providers, tool servers, database runtimes, and client applications, the system must enforce strict context propagation standards.1 AI transactions are transport-independent, frequently traversing HTTP REST, WebSockets, stdio subprocess pipes (for local tool integrations), and message queues within a single transaction.3

The system utilizes the W3C Trace Context specification as its baseline.3 The traceparent and tracestate parameters must be injected into all outgoing execution payloads.3 In environments where standard HTTP headers are unavailable—such as Model Context Protocol (MCP) servers operating over JSON-RPC stdio pipes—instrumentations must propagate context inside the JSON-RPC request parameters using the params._meta property bag.3

For example, a compliant JSON-RPC payload propagating a W3C Trace Context and associated baggage is structured as follows 3:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "calculate_disbursement",
    "arguments": {
      "base_amount": 500.0,
      "is_promotional": false
    },
    "_meta": {
      "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
      "tracestate": "vendor_key=opaque-routing-state",
      "baggage": "subject.hash=sha256_subject_hash,tenant.hash=sha256_tenant_hash,environment=prod"
    }
  },
  "id": "req_42"
}
```

Baggage should be treated as a propagation surface, not a private vault with a lanyard. Do not place raw user IDs, raw tenant IDs, credentials, policy details, or sensitive authorization state in baggage. Use opaque correlation IDs or hashes, and keep high-sensitivity authorization context inside the trusted gateway or policy engine.

The receiving server extracts the traceparent from the _meta block to establish parent-child relationships, ensuring that local tool execution spans are bound to the parent trace initiated by the client orchestrator.3

## **GenAI Span Taxonomy and Semantic Conventions**

To decouple instrumentation from specific platforms, the platform must standardize its telemetry around the OpenTelemetry GenAI Semantic Conventions (v1.41) 3 and the OpenInference tracing specification.5

The OpenTelemetry conventions are currently in *Development* status.3 To manage transitions and protect against breaking changes in production environments, instrumentations must use the environment variable OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental.3 This configuration forces the runtime to emit the latest experimental conventions while maintaining compatibility profiles on downstream collectors.3

### **Artifact 3: GenAI Span Taxonomy**

OpenTelemetry GenAI semantic conventions and OpenInference conventions evolve. Production systems should pin a configured convention version, translate provider-specific fields at the collector/gateway layer, and preserve compatibility mappings during upgrades.

| Span Name Format | Span Kind | Required Attributes | Optional / Provider-Specific Attributes | Sensitive Fields / Redaction Strategy |
| :---- | :---- | :---- | :---- | :---- |
| `create_agent` | INTERNAL | `agent.id`, `agent.name`, `agent.version`, `service.name` | agent description, owner, deployment profile | Redact credentials, hidden prompts, internal policy text. |
| `invoke_agent {agent.name}` | INTERNAL / CLIENT | `trace_id`, `session.hash`, `agent.id`, `workflow.id` | agent drift score, routing profile, tool manifest hash | Hash subject identifiers; avoid raw user or tenant IDs. |
| `invoke_workflow {workflow.name}` | INTERNAL | `workflow.id`, `workflow.name`, `workflow.run_id`, `workflow.status` | step count, retry count, budget state | Log state hashes and summaries, not raw payloads by default. |
| `llm.inference {model.route}` | CLIENT | provider name, request model/route, response model/route, request id, status | input/output/cached/reasoning tokens where exposed | Prompt/completion text should be redacted or stored by secure reference. |
| `retrieval {data_source.id}` | INTERNAL | data source ID, query hash, tenant/scope hash, candidate count, authorization filter version | document IDs, scores, chunk IDs, source version hashes | Do not log raw document text in general traces. |
| `rerank {reranker.route}` | INTERNAL / CLIENT | reranker route, candidate count, latency, status | top-k IDs, score distribution | Use document IDs and hashes; avoid raw snippets unless securely referenced. |
| `execute_tool {tool.name}` | INTERNAL / CLIENT | tool name, tool version, action class, payload hash, authorization decision, status | tool result hash, quota consumed, idempotency hash | Redact tool args/results; store secure reference for sensitive payloads. |
| `guardrail {policy.name}` | INTERNAL | policy id, policy version, decision, risk class | redaction count, refusal reason class, detector score | Do not log raw violating text unless policy allows secure evidence capture. |
| `human_review {queue.name}` | INTERNAL | review request id, risk tier, status, reviewer role class | review duration, outcome, override reason class | Redact reviewer/user identity or store under audit controls. |

### **Model Context Protocol Tracing Integration**

The Model Context Protocol (MCP) represents a critical integration surface for agentic tooling.1 Introduced in OTel v1.39, the MCP semantic conventions dictate that instead of generating duplicate, overlapping spans, the MCP middleware must enrich the existing execute_tool span with protocol-specific metadata.3  
When an agent invokes a tool through an MCP server, the instrumentation layer appends the following attributes to the active execute_tool span 3:

* mcp.method.name: The JSON-RPC method, e.g., tools/call.3  
* mcp.session.id: The unique cryptographic session identifier.3  
* mcp.protocol.version: The active protocol version string, e.g., 2025-06-18.3  
* rpc.response.status_code: The JSON-RPC error code, e.g., -32602 (invalid params).3  
* jsonrpc.request.id: The string representation of the request ID.3  
* network.transport: Set to pipe for STDIO-based local servers, or tcp for HTTP/SSE remote servers.3

If a tool call returns with isError: true inside the CallToolResult object, the instrumentation must set the span's error.type attribute to tool_error and update the overall span status to Error.3

## **The Multi-Plane Telemetry Map**

To construct a comprehensive representation of an AI application's behavior, telemetry must be gathered across multiple, distinct planes. These planes are not isolated; they represent correlated dimensions of a single computational system. For example, a latency spike observed on the Infrastructure Plane is diagnostic only when correlated with a route change on the Inference Plane or a cache miss on the Retrieval Plane.1

```text
TELEMETRY PLANES MAP

+--------------------------+     +--------------------------+
| Infrastructure Plane     |     | Inference Plane          |
| CPU/GPU utilization      |     | model route/provider     |
| memory/cache pressure    |     | input/output tokens      |
| queues and workers       |     | TTFT / ITL / finish      |
+-------------+------------+     +-------------+------------+
              |                                |
              v                                v
+--------------------------+     +--------------------------+
| Retrieval Plane          |     | Tool / Action Plane      |
| query hashes             |     | tool name/version        |
| candidate counts         |     | payload hash             |
| source/version IDs       |     | idempotency / status     |
| citation verification    |     | post-action verification |
+-------------+------------+     +-------------+------------+
              |                                |
              v                                v
+--------------------------+     +--------------------------+
| Agent / Workflow Plane   |     | UX / Trust Plane         |
| plan steps               |     | user corrections         |
| repair loops             |     | retry/cancel behavior    |
| no-progress states       |     | disclosures shown        |
| escalation triggers      |     | citation interactions    |
+-------------+------------+     +-------------+------------+
              |                                |
              v                                v
+--------------------------+     +--------------------------+
| Governance Plane         |     | Cost / Semantic Plane    |
| maker-checker state      |     | spend and cost velocity  |
| approvals / overrides    |     | drift/canary signals     |
| SARC constraints         |     | refusal distributions    |
| audit chain events       |     | grounding/entailment     |
+--------------------------+     +--------------------------+

Correlation spine:
  trace_id -> span_id -> workflow_id -> session.hash -> tenant.hash
  plus artifact IDs: document_id, tool_call_id, approval_request_id, route_id
```

The table below outlines the specific attributes, metrics, and correlation keys required to bind these planes into a unified analytical graph:

| Telemetry Plane | Core Attributes | Primary Metrics | Correlation Key |
| :---- | :---- | :---- | :---- |
| **Infrastructure** | container.id, gpu.device.id, process.pid 18 | gpu_cache_usage_perc, num_requests_waiting 19 | trace_id (W3C standard) |
| **Inference** | gen_ai.request.model, gen_ai.provider.name 6 | gen_ai.client.token.usage, time_to_first_token 3 | span_id (Model-call level) |
| **Retrieval** | gen_ai.data_source.id, document.id 13 | document.score, retrieval.latency 16 | document.id |
| **Tool** | gen_ai.tool.name, mcp.session.id 3 | tool.execution_time, tool.error_rate | idempotency_key |
| **Agent** | gen_ai.agent.id, workflow.run_id 13 | agent.run_duration, repair_loop_count | workflow.run_id |
| **UX & Trust** | session.id, user.id 20 | citation_click_rate, user_correction_count | session.id |
| **Governance** | maker_id, checker_id, risk_tier 2 | review_duration_seconds, override_rate | approval_requests.id 2 |
| **Cost** | usage.cost.total, tenant_id 20 | cost_velocity_usd, unattributed_cost_ratio | tenant_id |
| **Semantic** | embedding.model_name 16 | semantic_distance, entailment_drift_score | embedding.model_name |

## **Token Telemetry and Inference Economics**

Tokens represent the fundamental currency and state footprint of Generative AI workloads.1 Tracking token metrics is crucial not only for financial auditing, but also for identifying systemic failure modes and performance regressions in production architectures.1

### **Artifact 5: Token Telemetry Model**

The Token Telemetry Model decomposes token usage into granular components to isolate the economic characteristics of every step:

```
Total Token Footprint  
├── Prompt (Input) Tokens  
│   ├── User Message Input  
│   ├── System Instructions & Prompt Templates  
│   ├── Context-Injected Tokens (RAG documents, DB schemas)  
│   └── Memory-Injected Tokens (Historical chat context)  
├── Cached Input Tokens  
│   ├── Cache Read Tokens (Hits: usage.cache_read.input_tokens)  
│   └── Cache Creation Tokens (Misses: usage.cache_creation.input_tokens)  
└── Completion (Output) Tokens  
    ├── User-Visible Output Tokens  
    ├── Deliberative / Internal Computational Tokens (usage.reasoning.output_tokens)  
    ├── Tool Schema / Payload Tokens  
    └── Wasted / Abandoned Tokens (Truncated generations, cancelled streams)
```

The table below maps specific token metrics to their operational diagnostic value:

| Token Metric Attribute | Telemetry Source | Systemic Pathology Detected | Diagnostic Signature / Behavioral Pattern |
| :---- | :---- | :---- | :---- |
| `gen_ai.usage.input_tokens` | OTel/OpenInference or gateway-normalized provider field | **Context Flooding** | Monotonically growing input size, high prefill latency, falling evidence density. |
| `gen_ai.usage.output_tokens` | OTel/OpenInference or gateway-normalized provider field | **Verbosity Drift** | Output length rises for stable task profiles without quality gain. |
| `gen_ai.usage.cached_input_tokens` | Provider-specific / gateway-normalized | **Cache Starvation or Cache Regression** | Cached-token ratio drops after prompt/template/router changes. |
| `gen_ai.usage.cache_creation_tokens` | Provider-specific / gateway-normalized | **Cache Thrash** | High cache creation paired with low reuse. |
| `gen_ai.usage.reasoning_tokens` | Optional/provider-specific | **Deliberation Runaway** | Hidden/reasoning token budget rises without improved answer quality. Do not log hidden reasoning text. |
| `embedding.input_tokens` | Embedding gateway / provider metadata | **Embedding Cost Spike** | Corpus or query expansion increases embedding spend unexpectedly. |
| `rerank.input_tokens` | Reranker gateway / model metadata | **Reranker Overload** | Too many low-signal candidates passed to expensive scoring. |
| `wasted_tokens_count` | Custom gateway metric | **Cancelled / Abandoned Generation** | Tokens generated after user cancellation, timeout, or route failure. |
| `repair_loop_tokens` | Orchestrator metric | **Format Repair Loop** | Repeated schema repair consumes increasing token budget. |
| `retry_tokens` | Gateway retry ledger | **Retry Storm** | Repeated attempts inflate spend and latency after transient errors. |

### **Mathematical Modeling of Loop Token Accumulation**

In recursive agentic loops (such as ReAct or planning patterns), context size grows quadratically as the history of prior steps, tool execution results, and formatting exceptions accumulates over consecutive turns.1 The cumulative prompt tokens T_input consumed across an N-turn execution path is modeled by the quadratic context-accumulation equation:  
T_input(N) = N * S + (u * N * (N + 1)) / 2 + (r * N * (N - 1)) / 2  
Where:

* S is the fixed system prompt and tool schema definition size in tokens.1  
* u is the average size of new incoming tokens injected per iteration (the user's follow-up inputs, formatting validation exceptions, or tool outputs).1  
* r is the average model generation output size in tokens per turn.1

If an agent enters an infinite loop, this quadratic token accumulation can rapidly exhaust API budgets and trigger denial-of-wallet incidents.1 Therefore, strategic telemetry must track T_input dynamically, enabling gateways to terminate execution paths before resource limits are breached.1

## **Latency Decomposition and Performance Profiling**

In generative AI deployments, aggregate "inference latency" is an insufficient metric. It hides the underlying performance characteristics of the system, preventing SREs from identifying whether a slowdown is caused by network congestion, database performance, or hardware bottlenecks.22

### **Prefill vs. Decode Phase Mechanics**

Large Language Model inference executes across two distinct stages with fundamentally different computing characteristics and hardware constraints 7:

1. **Prefill Stage (Prompt Ingestion):** The model processes the entire prompt (including system instructions, retrieved document chunks, and chat history) in parallel, building the key-value (KV) cache.7 This stage is compute-bound, heavily utilizing the GPU's Tensor Cores.7 Prefill speed defines the Time to First Token (TTFT).7  
2. **Decode Stage (Autoregressive Generation):** The model generates subsequent completion tokens sequentially, one by one.7 Each step executes a forward pass that reads the existing KV cache from GPU High Bandwidth Memory (HBM) to generate the next token.7 This stage is memory-bandwidth-bound, leaving GPU compute cores underutilized.7 Decode speed defines the Inter-Token Latency (ITL).7

```text
PREFILL VS DECODE

Prompt / Context Tokens
  system instructions
  user message
  retrieved chunks
  tool schemas
        |
        v
+-----------------------------+
| Prefill Phase               |
| compute-bound               |
| processes prompt in bulk    |
| builds KV cache             |
| drives TTFT                 |
+-------------+---------------+
              |
              v
        KV Cache Ready
              |
              v
+-----------------------------+
| Decode Phase                |
| autoregressive              |
| memory-bandwidth sensitive  |
| generates one token step    |
| drives inter-token latency  |
+-------------+---------------+
              |
              +--> Output Token 1
              +--> Output Token 2
              +--> ...
              +--> Output Token N
```

### **Artifact 6: Latency Decomposition Model**

To isolate these bottlenecks, the system decomposes end-to-end transaction latency into stage-specific components:

| Latency Component | Telemetry Metric Source | Bottleneck / Constraint | SRE Diagnostic Action |
| :---- | :---- | :---- | :---- |
| **Input Validation** | Gateway Trace | CPU-bound network proxy | Verify gateway thread pool scaling.1 |
| **Parser / OCR** | parser.latency | CPU-bound text extraction | Monitor container memory limits.1 |
| **Retrieval** | db.execution_time | Database index lookup | Tune HNSW indexing parameters.1 |
| **Reranking** | reranker.latency | GPU-bound cross-encoder | Batch candidate documents for scoring. |
| **Queue Waiting** | gen_ai.latency.time_in_queue 19 | Serving engine congestion | Scale GPU replicas or apply rate limits.19 |
| **Prefill Phase** | vllm:time_to_first_token_seconds 19 | GPU compute (FLOPS) | Enable chunked prefill or prefix caching.7 |
| **Decode Phase** | vllm:time_per_output_token_seconds 19 | GPU memory bandwidth | Quantize weights (e.g., W8A8 or W4A16).8 |
| **Tool Execution** | tool.execution_time | Downstream API / Network | Enforce strict timeout thresholds.2 |
| **Voice STT/TTS** | voice.ttfa | Audio streaming latency | Peer WebRTC transceivers closer to client.23 |
| **Human Review** | review_duration_seconds 2 | Operator queue backlog | Route complex transactions to backup queues.2 |

### **SRE Profiling Workflows and Metrics Collection**

To capture this granular data, SRE teams use a coordinated profiling stack 22:

* **Nsight Systems / NVTX:** Tracks kernel-level execution timelines, highlighting GPU synchronization stalls and inter-GPU communication waits.22  
* **NCCL Debug Logs (export NCCL_DEBUG=INFO):** Traces collective communication calls across multi-GPU setups, identifying interconnect bottlenecks.22  
* **vLLM Prometheus Metrics:** Collects serving engine performance signals on a 15-second scraping interval.19

SREs deploy the following PromQL queries to isolate prefill bottlenecks from decode bottlenecks over rolling 5-minute windows 22:

* **Average Prefill Duration (TTFT) per Request:**  
  AveragePrefillTime = increase(vllm:time_to_first_token_seconds_sum[5m]) / increase(vllm:time_to_first_token_seconds_count[5m])  
* **Average Inter-Token Latency (ITL) during Generation:**  
  AverageITL = increase(vllm:inter_token_latency_seconds_sum[5m]) / increase(vllm:inter_token_latency_seconds_count[5m])

## **AI Error Mechanics, Retries, and Routing Decisions**

In high-dimensional AI applications, standard HTTP status codes (such as 4xx and 5xx) are insufficient for diagnosing system failures. A model call can succeed transport-wise (returning HTTP 200) while failing completely at the semantic, syntactic, or safety layer.1

### **Artifact 7: AI Error and Retry Taxonomy**

| Failure Classification | Operational Trigger Scenario | Telemetry Error Code (`error.type`) | Logged Context Payload | Mitigation / Fallback Playbook |
| :---- | :---- | :---- | :---- | :---- |
| **Syntax Violation** | Model output cannot be parsed as required JSON/XML/tool format. | `syntax_decode_error` | Response hash, redacted excerpt if allowed, parser error class. | Enter bounded repair path or return structured failure. |
| **Schema Violation** | Output parses but omits required fields or violates schema. | `schema_validation_error` | Missing/invalid field names, schema version, validation summary. | Halt execution or repair; do not invent missing required fields. |
| **Semantic Violation** | Structurally valid output violates business logic or domain constraints. | `business_rule_error` | Rule ID, field hashes/values if safe, diagnostic summary. | Block action; route to correction or human review. |
| **Provider Refusal** | Provider refuses generation due to safety/policy. | `provider_refusal` | Refusal category, provider route, policy class. | Return refusal or use approved policy-equivalent fallback only when allowed. |
| **Citation Hallucination** | Output cites source not present or not authorized in retrieval context. | `invalid_citation` | Cited source ID, context inventory hash, retrieval ID. | Remove/suppress claim or regenerate with verified evidence. |
| **Unsupported Claim** | Claim lacks entailment or source support. | `unsupported_claim` | Claim hash, evidence IDs, entailment score/class. | Mark as unverified, request evidence, or suppress. |
| **Tool Argument Violation** | Tool payload fails schema, authorization, or semantic checks. | `tool_argument_error` | Tool name, schema version, payload hash, validation summary. | Block tool call; ask clarification or route to approval. |
| **Tool Execution Loop** | Agent repeats identical or equivalent tool calls. | `tool_loop_detected` | Payload hash, repetition count, workflow ID. | Halt loop, preserve state, return managed no-progress status. |
| **Unknown Action State** | Tool timeout or partial commit leaves state unclear. | `unknown_action_state` | Tool call ID, idempotency hash, pre/post verification status. | Hold, reconcile, compensate where possible, escalate. |
| **No-Progress State** | Agent revises plans or retries without material state change. | `no_progress_error` | State hash, plan diff summary, loop step count. | Replan once, ask user, or halt based on policy. |
| **Cross-Tenant Boundary Event** | Resource, retrieval result, cache, or tool request crosses tenant scope. | `tenant_scope_violation` | Tenant hash, resource hash, policy ID, boundary class. | Block, isolate affected route, create security incident. |

| Field Name | Type | Value Range / Pattern | Operational Security Purpose |
| :---- | :---- | :---- | :---- |
| `routing_id` | String | `rt_[route_profile]_[uuid]` | Primary key for route decision trace. |
| `trace_id` | String | W3C trace ID | Correlates route with full execution trace. |
| `tenant_hash` | String | `sha256:...` | Supports tenant-level analysis without exposing raw tenant ID. |
| `session_hash` | String | `sha256:...` | Correlates session-level route behavior. |
| `requested_route` | String | Route/profile name | Captures user/app requested capability floor. |
| `selected_route` | String | Approved route/profile name | Captures actual executed route. |
| `routing_reason` | Enum | `normal`, `failover`, `quota_throttled`, `latency_slo`, `cost_policy`, `quality_floor`, `safety_policy`, `cache_hit` | Explains why route changed. |
| `quality_floor` | String | Profile ID | Ensures selected route meets task requirements. |
| `capability_delta` | Array | Lost/preserved capability labels | Identifies degraded-mode impact. |
| `budget_state` | Object | remaining spend/tokens/quota | Prevents unbounded consumption and explains throttling. |
| `policy_version` | String | Policy manifest version | Makes route decision replayable. |
| `user_disclosure_required` | Boolean | true/false | Records whether user-visible disclosure was required. |
| `user_disclosure_shown` | Boolean | true/false | Verifies UI disclosure occurred when required. |
| `route_status` | Enum | `selected`, `blocked`, `degraded`, `failed_closed` | Records route outcome. |

## **Retrieval and Tool Observability Models**

In Retrieval-Augmented Generation (RAG) and tool-driven agent environments, strategic telemetry must prove the validity of context and verify the execution of external mutations.1

### **Artifact 9: Retrieval Observability Model**

To guarantee the structural integrity of RAG setups, the system logs the complete retrieval context. This model enforces the **Doctrine of "Provenance Before Relevance"**: no document chunk is admitted to the model-facing context unless the system can prove where it came from, what authority it carries, and what transformations it has undergone.1

```json
{
  "$schema": "https://ai-engineering.canon/schemas/retrieval-observability-v1.json",
  "retrieval_id": "ret_2026_06_11_1201",
  "trace_id": "8f92a10c7d3a4e9f9a1b6c5d4e3f2010",
  "query_parameters": {
    "original_query_hash": "sha256:original_query_hash",
    "original_query_redacted": "What are our operating margins for the machinery segment?",
    "rewritten_query_hashes": [
      "sha256:rewrite_1_hash",
      "sha256:rewrite_2_hash"
    ],
    "tenant_hash": "sha256:tenant_hash",
    "permission_filter_ids": [
      "finance_auditor",
      "executive"
    ],
    "policy_version": "retrieval_policy_v12"
  },
  "retrieved_documents": [
    {
      "document_id": "doc_xyz",
      "source_ref": "secure_payload_ref:source_doc_xyz",
      "source_version_hash": "sha256:source_version_hash",
      "chunk_id": "chunk_014",
      "relevance_score": 0.98,
      "page_number": 12,
      "bounding_box": {
        "x": 0.12,
        "y": 0.34,
        "width": 0.42,
        "height": 0.08,
        "coordinate_system": "normalized_page"
      },
      "transformation_pipeline": [
        {
          "step": "pdf_text_extract",
          "version": "parser_v3.2"
        },
        {
          "step": "chunking",
          "version": "chunker_v5",
          "chunk_hash": "sha256:chunk_hash"
        },
        {
          "step": "embedding",
          "version": "embedding_model_v2",
          "embedding_hash": "sha256:embedding_hash"
        }
      ],
      "claims_supported": [
        {
          "claim_id": "claim_001",
          "claim_hash": "sha256:claim_hash",
          "redacted_text_segment": "Operating margins for the Industrial Machinery segment rose to 14.2% in Q2 2026.",
          "support_status": "supported",
          "evidence_region": {
            "page_number": 12,
            "bounding_box": {
              "x": 0.12,
              "y": 0.34,
              "width": 0.42,
              "height": 0.08,
              "coordinate_system": "normalized_page"
            }
          }
        }
      ]
    }
  ],
  "verification_signals": {
    "nli_grounding_score": 0.98,
    "source_conflict_detected": false,
    "stale_cache_served": false,
    "authorization_checked": true,
    "citation_verification_status": "verified"
  }
}
```

This artifact should prove evidence lineage without dumping raw documents into general telemetry. Auditors need source IDs, secure references, hashes, coordinates, parser/chunking versions, and verification status. They do not need your observability database cosplaying as a data breach.

This schema guarantees that if an auditor inspects an answer, they can trace the exact bounding box and page number on the original document that supported the model's output.2

### **Artifact 10: Tool Call Trace Model**

Tool call telemetry must enforce strict segregation of duties and verify system states. When an agent executes a tool, the system utilizes the Saga Pattern, decomposing multi-step operations into compensatable, pivot, and retriable transactions to ensure eventual consistency across distributed services.2

```json
{
  "$schema": "https://ai-engineering.canon/schemas/tool-trace-v1.json",
  "tool_call_id": "tool_99201_A",
  "trace_id": "8f92a10c7d3a4e9f9a1b6c5d4e3f2010",
  "tool_specification": {
    "name": "calculate_disbursement",
    "schema_version": "1.4.0",
    "action_class": "non_idempotent_mutation",
    "tool_manifest_hash": "sha256:tool_manifest_hash"
  },
  "authorization": {
    "subject_hash": "sha256:subject_hash",
    "tenant_hash": "sha256:tenant_hash",
    "scoped_credential_lifetime_seconds": 900,
    "permission_gate": "maker_checker_approval_required",
    "approval_request_id": "approval_123"
  },
  "execution_payload": {
    "payload_hash": "sha256:payload_hash",
    "redacted_argument_summary": {
      "transaction_id": "TXN-2026-0812",
      "base_amount_class": "under_1000_usd"
    },
    "idempotency_key_hash": "sha256:idempotency_key_hash"
  },
  "state_verification": {
    "pre_action_state_hash": "sha256:f02c...",
    "post_action_state_hash": "sha256:a91b...",
    "system_of_record_commit_verified": true,
    "verification_status": "verified"
  },
  "reversibility": {
    "transaction_step": "PIVOT_TRANSACTION",
    "compensation_supported": true,
    "compensation_reference": "secure_ref:compensation_plan_456",
    "compensation_status": "not_required"
  },
  "result": {
    "status": "success",
    "error_class": null,
    "completed_at": "2026-06-11T12:04:30Z"
  }
}
```

Tool telemetry should log hashes, statuses, authorization decisions, and secure references. It should not spray raw compensation endpoints, secrets, or high-impact payloads into general observability.

This structure guarantees **Eventual Consistency Gating**: the conversational interface is blocked from speaking or displaying a completion confirmation (e.g., "Your payment has been sent") until the Post-Action Auditor verifies that the database commit successfully updated the system of record.2

## **Multi-Dimensional Cost Attribution**

Enterprise AI systems process high volumes of distributed transactions, making it critical to attribute operational expenses precisely.1

### **Artifact 11: Cost Attribution Model**

The Cost Attribution Model associates every unit of consumed resource back to its corresponding system entity, enabling real-time cost allocation and anomaly detection:

| Allocation Dimension | Primary Attribution Fields | Tracked Resource Component | Pricing Metrics Formula |
| :---- | :---- | :---- | :---- |
| **B2B Tenant** | tenant_id 20, tenant_tier 2 | Vector indexing, multi-tenant model calls.1 | Cost_tenant = sum(Cost_tokens + Cost_storage + Cost_review) 1 |
| **Interactive Session** | session.id 20 | User conversation history, memory read/writes.2 | Cost_session = sum_turns(T_input * P_input + T_output * P_output) |
| **Agent / Workflow** | gen_ai.agent.id 13, workflow.id 2 | Multi-step agent planning, self-reflection loops.1 | Cost_workflow = sum_steps(Cost_model + Cost_tools) |
| **Parsing & OCR** | parser.name, document.id 16 | Layout analysis, PDF rasterization, OCR hosting.23 | Cost_parse = N_pages * Price_page + t_compute * Price_compute |
| **Security Scanning** | guardrail.id | Input Prompt Shields, output ARGUS scans.1 | Cost_security = sum(Cost_classifiers + Cost_regex) |
| **Human Governance** | approval_requests.id 2 | Centralized queue-based maker-checker reviews.2 | Cost_human = t_review_minutes * Price_operator 1 |
| **Incident / Outage** | incident.id | Out-of-bounds runaway loops, thundering-herd retries.1 | Cost_incident = Cost_runaway_tokens + Cost_failed_retries 1 |

## **Semantic Drift and Behavioral Regression Monitoring**

Language models are highly dynamic and non-deterministic.1 Over time, changes in context distributions, silent provider updates, or updates to retrieval databases can cause gradual or sudden shifts in meaning, tone, and safety compliance.1 Because these regressions are semantic and behavioral, traditional statistical tests (such as KL divergence) fail to detect them, and infrastructure dashboards remain green.1

### **Artifact 12: Semantic Drift Model**

To detect and isolate behavioral regressions, the system deploys a multi-layered Semantic Drift Model, using triangulation across multiple independent dimensions:

```
  Semantic Drift Triangulation  
  ├── Dimensionality-Reduced Embedding Shift  
  │   ├── Cosine Distance from Reference Centroid (Threshold: > 0.15)   
  │   └── Reconstruction Loss via Trained Autoencoder (Threshold: > 3 STDEV)   
  ├── Task-Based Activation Analysis  
  │   └── Hidden Layer Activation Pattern Variance   
  ├── Natural Language Inference (NLI) Grounding Scores  
  │   └── Entailment vs. Contradiction Ratios on Reference Claims   
  └── Scheduled Canary Prompt Inspections  
      └── Scheduled Execution of Curated Prompts (Similarity, Perplexity, Tone) 
```

The table below outlines the implementation details and metrics for each validation layer:

| Validation Layer | Underlying Core Algorithm | Telemetry Metrics Captured | Regression Warning Threshold |
| :---- | :---- | :---- | :---- |
| **Embedding Space** | PCA/UMAP projection, centroid shift, Wasserstein or cosine-distance comparison. | `semantic_distance_metric`, `centroid_shift`, `distribution_distance` | Threshold calibrated against baseline window and task domain. |
| **Reconstruction Loss** | Autoencoder or density model trained on baseline output embeddings. | `reconstruction_error`, `outlier_score` | Alert when sustained error exceeds calibrated baseline band. |
| **Domain Classifier** | Classifier distinguishing baseline vs. current outputs. | `classifier_auc_score`, `domain_shift_probability` | High separability indicates distribution shift requiring review. |
| **Canary Prompts** | Scheduled execution of curated prompts with fixed route/profile controls. | `canary_similarity_score`, `schema_pass_rate`, `policy_pass_rate` | Alert on sustained degradation against canary baseline. |
| **NLI / Evidence Support** | Cross-encoder or verifier scoring claim support against evidence. | `nli_entailment_ratio`, `unsupported_claim_rate` | Threshold set by task risk; high-impact domains use stricter floors. |
| **Refusal Distribution** | Clustering/classification of refusal and safety outcomes. | `refusal_rate`, `refusal_cluster_entropy`, `policy_category_shift` | Alert when refusal behavior shifts materially for stable task mix. |
| **User Correction Signals** | Analysis of edits, corrections, thumbs-downs, retries, and abandonments. | `user_correction_count`, `edit_distance`, `retry_after_answer_rate` | Treat as UX/behavior signal, not standalone truth label. |

## **The Green Dashboard Fallacy Diagnostic**

The Green Dashboard Fallacy is the critical diagnostic error of assuming an AI system is healthy based solely on infrastructure metrics.1 To prevent this, platform teams must monitor behavioral indicators of degradation that hide behind green infrastructure signals.1

### **Artifact 13: Green Dashboard Fallacy Diagnostic**

This diagnostic maps silent behavioral failures to their corresponding detection signals and telemetry check locations:

| Observed Behavioral Symptom | Green Infrastructure Signal | Hidden Systemic Failure | Telemetry Check Location / Correlation Key |
| :---- | :---- | :---- | :---- |
| **User Correction Spike** | HTTP 200 OK; latency <= 150 ms | Model is repeatedly outputting formatted but incorrect financial data.1 | user_correction_count correlated with edit_character_diff.2 |
| **Citation Click Collapse** | CPU/GPU load normal; database active | Model is generating decorative, ungrounded citation badges post-hoc.1 | citation_click_rate drops below 15.0% over 1 hour.2 |
| **Stale Cache Overuse** | TTFT <= 10 ms (Cache hits) 2 | System is serving outdated policy data, bypassing live databases.1 | stale_cache_served matches expired Redis TTL metadata.2 |
| **No-Progress Agent Loops** | GPU utilization active; APIs active | Agent is stuck repeating identical tool calls with different formatting.1 | state_repetition_count (C_rep >= 2) inside the active task plan.1 |
| **Reviewer Complacency** | Queue throughput high; no alerts | Reviewers are rubber-stamping high-risk payments without verification.2 | average_modal_approval_duration drops below 350 ms.2 |
| **Silent Model Downgrade** | Cost drops; system remains online | Gateway proxy silently routed requests to smaller, low-quality models.2 | selected_model differs from client's requested_model.2 |

### **Artifact 14: AI Observability Dashboard Taxonomy**

To make behavioral health visible to operators, the system organizes telemetry across six specialized, correlated dashboard views:

```text
AI OBSERVABILITY DASHBOARD TAXONOMY

+--------------------------+     +--------------------------+
| Serving Health           |     | Behavioral Health        |
| queue depth              |     | groundedness ratio       |
| TTFT / ITL               |     | schema pass rate         |
| GPU/KV cache pressure    |     | unsupported claims       |
| provider errors          |     | refusal distribution     |
+--------------------------+     +--------------------------+

+--------------------------+     +--------------------------+
| Retrieval & Evidence     |     | Agent & Tool Behavior    |
| retrieval fan-out        |     | tool retries             |
| citation verification    |     | no-progress loops        |
| stale cache use          |     | action verification      |
| source conflicts         |     | idempotency failures     |
+--------------------------+     +--------------------------+

+--------------------------+     +--------------------------+
| Governance & Review      |     | Cost & Drift             |
| maker-checker state      |     | tenant spend             |
| approval latency         |     | cost velocity            |
| override rate            |     | embedding drift          |
| break-glass events       |     | canary regressions       |
+--------------------------+     +--------------------------+
```

## **Telemetry Privacy, Redaction, and Compliance**

Strategic telemetry can capture prompts, retrieved documents, tool arguments, model responses, reviewer decisions, and action traces. These payloads may contain PII, PHI, payment data, credentials, secrets, proprietary code, internal policies, or regulated business records. Observability must not become the vulnerability it was designed to diagnose.

The default posture should be:

* capture metadata by default;
* capture raw payloads only when explicitly allowed;
* redact before general telemetry storage;
* store sensitive payloads behind controlled references;
* log access to sensitive telemetry;
* retain sensitive payloads for the shortest policy-compatible period;
* keep audit evidence sufficient for replay without dumping raw secrets everywhere.

### **Redaction and Payload Handling**

Regex and NER filters are useful but incomplete. They can miss secrets, over-redact important evidence, or fail on unfamiliar formats. Redaction should therefore be layered:

| Layer | Purpose |
| :--- | :--- |
| **Structured Field Policy** | Never log known secret fields, credentials, tokens, private keys, or raw auth headers. |
| **Classifier / Regex / NER Scan** | Detect common PII, payment data, credentials, and regulated entities. |
| **Source-Aware Redaction** | Apply stricter rules to medical, legal, financial, HR, tenant-private, and security-sensitive payloads. |
| **Secure Reference Storage** | Store sensitive payloads outside general trace stores with purpose-bound access. |
| **Access Auditing** | Log who accessed sensitive payload references and why. |
| **Retention Control** | Expire sensitive payloads separately from lower-risk metadata. |

### **External Payload Reference-Only Tracing**

```text
REFERENCE-ONLY TELEMETRY FLOW

[ Application / Gateway ]
  receives prompt, tool payload, retrieved text, or model output
        |
        v
[ Redaction and Classification Gate ]
  classify sensitivity
  redact safe fields
  decide metadata-only vs secure-reference capture
        |
        +--> low-risk metadata
        |       write directly to trace span
        |
        v
[ Secure Payload Vault ]
  encrypted storage
  short TTL
  purpose-bound access
  access logging
  tenant/user scope controls
        |
        v
[ Trace Collector ]
  stores metadata only:
    payload_ref
    payload_hash
    sensitivity class
    retention class
    access policy id
```

Reference-only tracing minimizes sensitive payload exposure. It does not make telemetry “PII-free” by magic wand; metadata can still be sensitive, and payload references require access control, retention policy, and audit logs.


### **Artifact 15: Telemetry Privacy and Redaction Model**

The table below defines the content capture and redaction policies enforced by the platform:

| Content Class | Captured Data Format | Storage Location / Substrate | Access Control Rules | Retention Period | Compliance Enforcement |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **User Prompts** | Metadata, hash, redacted excerpt, or secure payload reference. | Secure payload vault if retained; metadata in trace store. | Purpose-bound access; audited retrieval. | Short TTL by default; policy-defined extension for incidents. | Deletion/export hooks where legally required. |
| **API Credentials / Secrets** | Never intentionally captured; block or hash only for detection event. | None for raw secret; detection event in security log. | Security team only for detection metadata. | Minimal retention for incident evidence. | Secret scanners and log egress controls. |
| **Tool Arguments** | Payload hash, redacted summary, schema version, secure reference when needed. | Action ledger / secure payload vault. | Auditor/security access by purpose and role. | Based on audit and transaction requirements. | Signed ledger and access logs. |
| **System Prompts / Templates** | Version ID, template hash, release reference; exact text only in controlled registry. | Prompt/model registry, not general traces. | Dev/security/governance access. | Release lifecycle retention. | Change-control and approval logs. |
| **Model Completions** | Metadata, hash, redacted excerpt, or secure payload reference. | Secure payload vault if retained. | Purpose-bound access with audit. | Short TTL by default; longer only for incidents/evals. | Privacy review and retention policy. |
| **Citation Evidence** | Source ID, page/section/coordinates, source version hash, secure evidence reference. | Document registry / evidence store. | Same or stricter scope as source document. | Bound to source lifecycle and audit policy. | RLS/ACL checks and citation verification. |
| **Trace Metadata** | Normalized numeric/string attributes, status, hashes, IDs. | Central telemetry store. | SRE/developer access depending on sensitivity. | Operational retention window. | Redaction checks before ingestion. |
| **Human Review Data** | Review request ID, outcome, role class, redacted comments, evidence refs. | Review/audit system. | Reviewer, governance, audit roles. | Governance/audit retention policy. | Access audit and policy review. |

## **Alerting and SRE SLO Design**

In strategic telemetry, Service Level Objectives (SLOs) must be defined over behavioral and semantic metrics to protect user trust and operational safety.1

### **Artifact 16: Alerting and SLO Model**

The SRE team configures and monitors the following behavioral SLOs and alerting thresholds:

| SLO Category | Target SLI Metric | SLO Target Threshold | Warning Alert Threshold | Critical Alert Threshold | Runbook / Automated Containment Action |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Semantic Health** | Claim support / entailment by task profile. | Calibrated per domain and risk tier. | Sustained support drop outside baseline band. | High-impact route falls below required evidence floor. | Freeze rollout, route to safer profile, require evidence refresh. |
| **Action Integrity** | Tool schema and post-action verification status. | High-impact actions require verified state. | Repeated validation failures on any tool route. | High-impact mutation has unknown or failed verification. | Block affected route; hold/reconcile/compensate where possible. |
| **Cost Control** | Cost velocity and budget consumption. | Spend remains within tenant/workflow budget. | Burn rate exceeds forecast. | Budget breach or denial-of-wallet pattern. | Trip circuit breaker, throttle, or require approval. |
| **Loop Containment** | No-progress count and repeated state hash. | Loops halt within workflow profile. | Repeated state detected. | Repeated state plus rising cost/tool calls. | Halt agent, preserve state, request clarification or escalate. |
| **Trust Calibration** | User corrections, abandonment, disclosure acknowledgement, review overrides. | Stable within task baseline. | Correction/abandonment spike. | High-risk workflow shows systematic reviewer/user miscalibration. | Add targeted cognitive forcing, review UI, or route audit. |
| **Tenant Safety** | Cross-tenant access/cache/retrieval mismatch events. | No accepted cross-tenant boundary violation. | Blocked mismatch event detected. | Confirmed exposure or repeated attempted boundary crossing. | Isolate affected scope, revoke implicated credentials, create incident. |
| **Privacy / Redaction** | Sensitive payload exposure events. | No raw secrets in general telemetry. | Redaction detector catches sensitive field before storage. | Sensitive payload reaches unauthorized telemetry sink. | Quarantine trace, revoke exposed secret, investigate access. |
| **Fallback Integrity** | Route downgrade with disclosure and quality-floor preservation. | All degradations are policy-preserving and observable. | Fallback spike or missing disclosure. | Unsafe fallback or silent downgrade on high-impact task. | Disable route, fail closed, or require user/reviewer choice. |

## **Systemic Cross-Canon Handoff Map**

Strategic telemetry provides the evidence substrate used across the canon. It connects behavioral health, cost, retrieval, tool execution, governance, privacy, evaluation, audit, and incident response.

| Target Canon Report | Functional Domain | Core Telemetry Handoff | Operational Integration Rule | Fallback / Degraded Protocol |
| :---- | :---- | :---- | :---- | :---- |
| **AI-ENG-B** | Context and State Governance | Context object IDs, memory inclusion events, compaction traces. | State changes must be traceable across route switches and summaries. | Preserve state hashes and continuity checkpoints. |
| **AI-ENG-D** | Corpus Engineering | Source IDs, source version hashes, provenance, lifecycle state. | Corpus-derived evidence must retain lineage in traces. | Exclude or quarantine unknown-provenance sources. |
| **AI-ENG-E** | Retrieval Pipeline | Retrieval IDs, query hashes, candidate counts, citation verification. | Retrieval traces must show authorization, source version, and evidence sufficiency. | Use managed no-evidence response if retrieval cannot be trusted. |
| **AI-ENG-F** | Freshness and Conflict Detection | Source age, cache age, conflict flags, freshness status. | Telemetry must expose stale/conflicting evidence. | Block stale high-impact answers or require refresh. |
| **AI-ENG-L** | Serving Architecture | TTFT, ITL, queue wait, route, cache, model/provider status. | Serving decisions must correlate with user-visible behavior and cost. | Shift to approved fallback route only if quality floor holds. |
| **AI-ENG-M** | Agentic Orchestration | Workflow run IDs, loop counts, no-progress state hashes. | Agents must emit enough telemetry to halt and replay loops. | Halt, replan, clarify, or escalate on repeated no-progress. |
| **AI-ENG-N** | Tool Contracts | Tool call IDs, schema versions, payload hashes, error classes. | Tool traces must prove schema, authorization, and idempotency status. | Block or hold unknown/high-impact tool states. |
| **AI-ENG-O** | Action Verification | Pre/post state hashes, verification status, action ledger. | Completion claims require verified state telemetry. | Hold, reconcile, compensate, or escalate unknown state. |
| **AI-ENG-P** | Multimodal Understanding | Parser versions, OCR confidence, evidence coordinates, media refs. | Visual/document evidence must be inspectable without leaking raw payloads. | Use secure evidence references or manual verification. |
| **AI-ENG-Q** | Voice Interaction | STT/TTS latency, transcript confidence, turn/endpointing events. | Voice degradation and confirmation states must be traceable. | Switch to text/card confirmation for high-impact actions. |
| **AI-ENG-R** | UI Agents | Browser session IDs, DOM snapshots hashes, action verification. | UI actions must be observable from observation to post-action state. | Pause automation on drift or uncertainty. |
| **AI-ENG-S** | Production Pathologies | Error classes, malformed outputs, repair loops, false success signals. | Behavioral pathologies require typed telemetry and replay traces. | Contain, repair, or route to degraded mode. |
| **AI-ENG-T** | Boundary Defense | Tenant scope, authorization decisions, cache scope, redaction events. | Boundary violations must emit security telemetry without leaking payloads. | Fail closed and create incident record when scope cannot be trusted. |
| **AI-ENG-U** | Supply Chain Security | Artifact hashes, model signatures, parser/tool versions, sandbox events. | Loaded artifacts must be traceable to approved supply-chain records. | Quarantine unsigned or anomalous artifacts. |
| **AI-ENG-V** | Resource Abuse | Token burn, cost velocity, quota burn, retry storms, queue depth. | Resource anomalies must be observable by tenant/session/workflow. | Throttle, circuit-break, or require approval. |
| **AI-ENG-W** | UX Resilience | Fallback route, disclosure shown, preserved state, degraded status. | Degraded mode must be traceable as a product state. | Use approved degraded mode, partial answer, review, or fail closed. |
| **AI-ENG-X** | User Trust and Transparency | User corrections, disclosures, citation interactions, contestability events. | Trust signals must be interpreted as behavioral telemetry, not truth proof. | Surface clearer status/evidence or route to review. |
| **AI-ENG-Y** | High-Impact Workflow Design | Approval request IDs, maker/checker state, review outcomes, break-glass events. | Governance actions require audit-grade telemetry. | Hold execution until approval/reconciliation is traceable. |
| **AI-ENG-AA** | Evaluations | Golden traces, canary outputs, drift signals, adversarial cases. | Evaluation harnesses consume production-shaped telemetry. | Block release on telemetry-backed regression. |
| **AI-ENG-AB** | Audit and Replay | Trace IDs, payload hashes, secure references, policy versions, action ledgers. | Replay must reconstruct the decision path without raw uncontrolled logs. | Preserve redacted, hash-bound evidence in audit store. |
| **AI-ENG-AC** | Incident Response | Incident IDs, containment events, route/corpus/tool/cache quarantine. | Incidents require structured telemetry for scope and timeline reconstruction. | Quarantine affected route/artifact/cache/tool and notify owners. |
| **AI-ENG-AD** | Governance and Compliance | Policy version, review status, retention class, access logs. | Governance defines what telemetry is mandatory, restricted, or deleted. | Route telemetry exceptions to accountable owner. |
| **AI-ENG-AJ** | Reference Architecture | Trace collector, policy-aware gateway, secure payload vault, audit store. | Reference systems should implement strategic telemetry by default. | Use metadata-first, reference-only tracing for sensitive payloads. |

## **Strategic Conclusions and Architectural Recommendations**

To transition from ad-hoc monitoring to high-assurance behavioral governance, enterprise platforms must treat telemetry as core software infrastructure.1 Based on the analyses compiled in this report, the following four strategic principles are recommended for deployment architectures:

1. **Centralize Telemetry at the Gateway Layer:** Avoid writing custom instrumentation, rate-limiting, and error-handling logic inside individual application services.2 Centralize strategic telemetry collection within a high-performance, budget-aware runtime gateway positioned entirely outside the model's cognitive boundary.1  
2. **Enforce Strict Gating Before Verifications:** Never allow conversational interfaces to generate verbal or text-based confirmation claims until the Post-Action Auditor verifies that the database transaction has been successfully committed in the system of record.2 Spoken or generated claims must never outrun physical reality.2  
3. **Secure Caches against Timing Side-Channels:** Formulated semantic cache keys must be cryptographically bound to the tenant ID and user permissions.1 Serving runtimes must deploy selective prefix isolation (such as the CacheSolidarity framework) to prevent timing side-channel probes from exfiltrating private context.1  
4. **Isolate High-Risk Content and Payloads:** Enforce a zero-trust payload logging policy.1 Strip credentials at the gateway, run ARGUS output filters to redact PII, and utilize reference-only tracing to store sensitive inputs in secure, short-TTL external storage rather than writing them to centralized, persistent trace collectors.1

## **Durable Principles of Strategic Telemetry**

1. **Green Infrastructure Does Not Prove Behavioral Health**  
   HTTP 200, low latency, and normal GPU utilization can coexist with hallucinations, tenant leaks, false success, stale cache, and unsafe actions.

2. **Trace the Workflow, Not Just the Request**  
   AI interactions span model calls, retrieval, tools, policy gates, human review, retries, routing, and state verification. A single request log is not enough.

3. **Telemetry Must Preserve Meaning-Level Evidence**  
   Strategic telemetry should capture claims, citations, evidence IDs, tool states, route decisions, and verification outcomes—not just duration and status.

4. **Sensitive Payloads Need Controlled References**  
   Raw prompts, completions, documents, and tool arguments should not be sprayed into trace stores. Use hashes, redacted summaries, and secure payload references.

5. **Token Metrics Are Economic and Behavioral Signals**  
   Token growth, cache misses, repair loops, reasoning-token spikes, and wasted tokens reveal cost bombs and behavioral pathologies.

6. **Latency Must Be Decomposed by Stage**  
   End-to-end latency hides parser, retrieval, queue, prefill, decode, tool, voice, and human-review bottlenecks.

7. **Tool Success Is Not Action Truth**  
   Tool traces must record authorization, idempotency, execution status, and post-action verification. A returned response is not proof of a committed state.

8. **Drift Requires Multiple Signals**  
   Embedding movement, canary prompts, NLI support, refusal shifts, schema pass rates, and user corrections should be triangulated. No single drift metric is oracle-grade. Obviously. The oracle budget was denied by finance.

9. **Telemetry Is a Security Boundary**  
   Observability systems hold sensitive operational evidence. They need redaction, access control, retention policy, and audit trails.

10. **Fallbacks and Degraded Modes Must Be Observable**  
   Model downgrades, cache responses, partial answers, review handoffs, and fail-closed states must emit structured events.

11. **Audit and Replay Depend on Telemetry Discipline**  
   Reproducibility requires trace IDs, payload hashes, policy versions, route decisions, evidence references, and action ledgers.

12. **Telemetry Without Action Is Decorative Plumbing**  
   Alerts must connect to runbooks, release gates, containment actions, governance review, and incident response.

#### **Works cited**

1. [KNOWLEDGE] - AI Engineering - Volume 7. S-V Failure, Security, and Hostile Environments  
2. [KNOWLEDGE] - AI Engineering - Volume 8. W-Y Resilience, Degraded Modes, and Human Trust  
3. AI Agent Observability 2026: Tracing & Monitoring Stack, accessed June 11, 2026, [https://www.digitalapplied.com/blog/ai-agent-observability-2026-tracing-monitoring-stack-guide](https://www.digitalapplied.com/blog/ai-agent-observability-2026-tracing-monitoring-stack-guide)  
4. Tracing Concepts - Arize AX Docs, accessed June 11, 2026, [https://arize.com/docs/ax/instrument/what-are-traces](https://arize.com/docs/ax/instrument/what-are-traces)  
5. OpenInference Specification - GitHub Pages, accessed June 11, 2026, [https://arize-ai.github.io/openinference/spec/](https://arize-ai.github.io/openinference/spec/)  
6. How OpenTelemetry Traces LLM Calls, Agent Reasoning, and MCP Tools | Greptime, accessed June 11, 2026, [https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions](https://greptime.com/blogs/2026-05-09-opentelemetry-genai-semantic-conventions)  
7. Prefill and Decode: A Technical Guide to the Two Phases of Inference - WEKA, accessed June 11, 2026, [https://www.weka.io/learn/ai-ml/prefill-and-decode/](https://www.weka.io/learn/ai-ml/prefill-and-decode/)  
8. Prefill vs Decode: LLM Inference Phases Explained - Redis, accessed June 11, 2026, [https://redis.io/blog/prefill-vs-decode/](https://redis.io/blog/prefill-vs-decode/)  
9. Optimizing LLM Inference: Prefill vs Decode, Latency vs Throughput | by Maghonei | Medium, accessed June 11, 2026, [https://medium.com/@maghonei/optimizing-llm-inference-prefill-vs-decode-latency-vs-throughput-80dbf00fc0ba](https://medium.com/@maghonei/optimizing-llm-inference-prefill-vs-decode-latency-vs-throughput-80dbf00fc0ba)  
10. 9 Best LLM Drift Monitoring Platforms in 2026 - Galileo AI, accessed June 11, 2026, [https://galileo.ai/blog/best-llm-output-drift-monitoring-platforms](https://galileo.ai/blog/best-llm-output-drift-monitoring-platforms)  
11. Semantic Drift Analysis - Emergent Mind, accessed June 11, 2026, [https://www.emergentmind.com/topics/semantic-drift-analysis](https://www.emergentmind.com/topics/semantic-drift-analysis)  
12. Translating Semantic Conventions - Phoenix - Arize AI, accessed June 11, 2026, [https://arize.com/docs/phoenix/tracing/concepts-tracing/translating-conventions](https://arize.com/docs/phoenix/tracing/concepts-tracing/translating-conventions)  
13. Semantic Conventions for GenAI agent and framework spans - OpenTelemetry, accessed June 11, 2026, [https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/)  
14. Semantic Conventions for Generative AI Agentic Systems (gen_ai.*) · Issue #35 - GitHub, accessed June 11, 2026, [https://github.com/open-telemetry/semantic-conventions-genai/issues/35](https://github.com/open-telemetry/semantic-conventions-genai/issues/35)  
15. Arize-ai/openinference: OpenTelemetry Instrumentation for AI Observability - GitHub, accessed June 11, 2026, [https://github.com/Arize-ai/openinference](https://github.com/Arize-ai/openinference)  
16. Semantic Conventions | openinference - GitHub Pages, accessed June 11, 2026, [https://arize-ai.github.io/openinference/spec/semantic_conventions.html](https://arize-ai.github.io/openinference/spec/semantic_conventions.html)  
17. Openinference Semantic Conventions - Arize AX Docs, accessed June 11, 2026, [https://arize.com/docs/ax/observe/tracing-concepts/openinference-semantic-conventions](https://arize.com/docs/ax/observe/tracing-concepts/openinference-semantic-conventions)  
18. OTEL.md - containers/kubernetes-mcp-server - GitHub, accessed June 11, 2026, [https://github.com/containers/kubernetes-mcp-server/blob/main/docs/OTEL.md](https://github.com/containers/kubernetes-mcp-server/blob/main/docs/OTEL.md)  
19. Observing vLLM with OpenTelemetry and Dash0, accessed June 11, 2026, [https://www.dash0.com/blog/observing-vllm-with-opentelemetry-and-dash0](https://www.dash0.com/blog/observing-vllm-with-opentelemetry-and-dash0)  
20. genai-otel-instrument - PyPI, accessed June 11, 2026, [https://pypi.org/project/genai-otel-instrument/0.1.24/](https://pypi.org/project/genai-otel-instrument/0.1.24/)  
21. LLM Monitoring & Drift Detection Guide | Metrics, Tools & Examples - Leanware, accessed June 11, 2026, [https://www.leanware.co/insights/llm-monitoring-drift-detection-guide](https://www.leanware.co/insights/llm-monitoring-drift-detection-guide)  
22. LLM Inference Optimization — Prefill vs Decode | by Robi Kumar ..., accessed June 11, 2026, [https://pub.towardsai.net/llm-inference-optimization-prefill-vs-decode-6e003d48b2ca](https://pub.towardsai.net/llm-inference-optimization-prefill-vs-decode-6e003d48b2ca)  
23. [KNOWLEDGE] - AI Engineering - Volume 6. P-R Multimodal and Interface-Controlling Systems  
24. sentinel/docs/DETECTION_METHODS.md at main · LLM-Dev-Ops ..., accessed June 11, 2026, [https://github.com/LLM-Dev-Ops/sentinel/blob/main/docs/DETECTION_METHODS.md](https://github.com/LLM-Dev-Ops/sentinel/blob/main/docs/DETECTION_METHODS.md)  
25. Monitor embedding drift for LLMs deployed from Amazon SageMaker JumpStart - AWS, accessed June 11, 2026, [https://aws.amazon.com/blogs/machine-learning/monitor-embedding-drift-for-llms-deployed-from-amazon-sagemaker-jumpstart/](https://aws.amazon.com/blogs/machine-learning/monitor-embedding-drift-for-llms-deployed-from-amazon-sagemaker-jumpstart/)

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