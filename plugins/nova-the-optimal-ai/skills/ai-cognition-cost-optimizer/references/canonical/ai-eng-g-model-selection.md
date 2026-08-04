# AI-ENG-G — Model Selection - Capability Fit, Deployment Fit & Failure Tolerance

## **Conceptual Foundations of Model Selection**

Model selection is the architectural discipline of matching model capability, deployment constraints, economics, governance requirements, and tolerated failure modes to the actual task graph of a production system.1 Within a mature engineering posture, model selection is treated as an architectural commitment rather than leaderboard shopping.2 Leaderboards, model cards, pricing pages, and provider claims represent raw, unvetted inputs; the final decision is a high-dimensional trade-off determined by task profile, user risk, operational constraints, and failure survivability.1  
This report establishes the core doctrine of Volume 3: **Capability fit before prestige: select the model whose strengths, limits, operating constraints, and failure behavior match the workflow, not the model with the most impressive general benchmark score.**  
The fundamental question of model selection is not which model is absolute best, but which model, or portfolio of models, provides sufficient capability for a specific workflow under the system’s constraints.4 This report builds a rigorous, profile-matching framework to answer that question, inheriting the concepts of layered control from AI-ENG-A, context-tenure from AI-ENG-B, and cost-per-success from AI-ENG-C.5

### **Conceptual Glossary**

| Term | Architectural Definition |
| :---- | :---- |
| **Model Selection** | The multi-criteria decision process of choosing and committing to a model or portfolio based on empirical validation against a specific system task graph.1 |
| **Capability Fit** | The alignment between a model's specialized functional behaviors (e.g., schema adherence, math deductive execution, visual grounding) and the demands of the task.1 |
| **Deployment Fit** | The physical compatibility of a model with target infrastructure, latency SLAs, region restrictions, security policies, and cost margins.6 |
| **Task Profile** | The formal specification of a workflow's input/output properties, required cognitive depth, and operational constraints.1 |
| **Reasoning Depth** | The quantity of computational steps and validation loops required to resolve a query, matching the task's complexity and economic boundaries.2 |
| **Context Fit** | The empirical performance of a model across variable context lengths, including retrieval-grounded synthesis and instruction-hierarchy preservation.1 |
| **Tool-Use Reliability** | The structural and semantic accuracy of a model when generating function-call parameters and managing state transitions.9 |
| **Structured-Output Reliability** | The mathematical guarantee or empirical probability that a model's output strictly adheres to a targeted schema.9 |
| **Modality Fit** | The capability of a model to ingest and synthesize multi-format tokens (visual, layout, audio, code) without downstream parsing failures.3 |
| **Failure Tolerance** | The system's capacity to detect, bound, and recover from specific model failures (e.g., hallucinations, refusals, schema drifts).10 |
| **Model Portfolio** | An orchestrated network of diverse models (e.g., embedding, reranking, routing, processing, fallback) structured to execute a joint workflow.4 |
| **Routing Policy** | The algorithmic rule set that assigns incoming queries to specific models based on intent, difficulty, budget, or latency.14 |
| **Fallback Chain** | The recovery sequence that directs a query to alternative models or human review when primary execution fails or degrades.2 |
| **Benchmark Proxy** | A public leaderboard score used as a coarse signal for candidate filtering, separate from task-specific evaluation.2 |
| **Model/System Card** | Provider documentation detailing training context, alignment parameters, safety baselines, and operating envelopes.17 |
| **License Fit** | The compliance of a model's legal terms with the host organization's commercial operations and intellectual property protection.17 |
| **Cost Per Successful Outcome** | The total cost of execution—including prefill, generation, caching, retries, and human validation—divided by the rate of valid outputs.5 |
| **Model Decision Record** | A durable architectural document justifying the selection, rejection, and operational boundaries of models within a system.20 |

## **Task Profile and Capability Fit**

Selecting a model requires a formal, systematic description of the workflow. The system's task graph dictates which capability dimensions are critical. The evaluation process must model these demands through a structured requirements profile.

### **Model Requirement Profile**

Before identifying candidate models, architects must define the task properties using the following specification parameters:

| Dimension | Specification Parameters | Architectural Impact |
| :---- | :---- | :---- |
| **Task Class** | Classification, Extraction, Synthesis, Multi-File Refactoring, Planning, Visual Mapping.1 | Dictates model category and required fine-tuning baselines.22 |
| **User & Risk Profile** | Internal operations, end-customer interaction, autonomous action; low-risk ideation to high-risk financial/medical execution.1 | Establishes validation requirements and fail-closed boundaries.1 |
| **Output Form** | Raw string, flat JSON schema, nested JSON schema, tool argument dictionary, markdown.9 | Determines the necessary generation enforcement mechanism (native, FSM, PDA).11 |
| **Required Modalities** | Text-only, visual layout, tabular image, multi-page PDFs, audio waveforms.3 | Filters candidates by native multi-modal perceptual encoders.3 |
| **Reasoning Depth** | Single-step, multi-step math, programmatic refactoring, adversarial planning.2 | Determines the allocation of inference-time compute (high-effort vs. low-effort).2 |
| **Context Length Needs** | Under 4K tokens, 32K window, 128K document set, 1M+ active token session.8 | Impacts VRAM reservation and continuous batching parameters.5 |
| **Tool Use Complexity** | Static function arguments, dynamic database querying, browser-use tool sequencing.3 | Requires specific alignment for tool state tracking and error recovery.9 |
| **Latency SLA** | Time-To-First-Token (TTFT) < 150ms; total execution < 1.0s.5 | Excludes large parameter options or slow inference-time compute tiers.22 |
| **Throughput Target** | Peak requests/sec, concurrent users, background batch load.5 | Dictates hardware configuration (GPU counts) and serving framework optimizations.5 |
| **Cost Ceiling** | Maximum allowable budget per successful transaction ($/million tokens).5 | Constrains the model portfolio to optimized open-weight or economy API tiers.6 |
| **Privacy Constraints** | Zero-retention cloud hosting, private cloud VPC, on-premise hardware.2 | Limits selection to specific cloud partners or hostable open-weight parameters.22 |
| **Language Scope** | English-only, high-resource multilingual, low-resource regional dialects, domain jargon.1 | Excludes models lacking representation in target pre-training corpuses.1 |
| **Unacceptable Failures** | Silent extraction omissions, math calculation errors, malformed tool arguments, policy evasion.9 | Demands strict fail-closed configurations and evaluation guardrails.2 |

### **Capability Fit Matrix**

The active production models of 2026 display highly differentiated capability matrices. Models are rated as Exceptional (E), Adequate (A), or Deficient (D) based on empirical behavior across core task vectors.

| Capability Vector | GPT-5.4 | Claude Opus 4.7 | Gemini 3 Pro | DeepSeek V4 | Llama 4 Scout | Qwen 3.5 72B |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Instruction Following** | E | E | A | A | A | A |
| **Reasoning Depth** | E | E | A | E | A | A |
| **Long-Context Integrity** | A | E | E | A | E | A |
| **Grounded Synthesis** | A | E | E | A | A | A |
| **Citation Discipline** | A | E | E | A | A | A |
| **Schema Adherence** | E | E | E | A | A | E |
| **Tool-Use Reliability** | E | E | E | A | A | A |
| **Multi-Step Planning** | E | E | A | E | A | A |
| **Code Competence** | E | E | A | E | A | E |
| **Math Performance** | E | E | E | E | A | A |
| **Multimodal Perception** | E | A | E | D | D | A |
| **Multilingual Coverage** | A | A | A | E | A | E |
| **Uncertainty Calibration** | A | E | A | D | D | D |
| **Robustness to Injections** | E | E | A | D | A | D |

### **Task-to-Model Fit Matrix**

This matrix maps common high-dimensional workflows to model requirements, ideal model classes, primary evaluation criteria, structural failure risks, and typical routing patterns.

| Workflow Class | Structural Requirements | Ideal Model Class | Critical Evaluation Criteria | Core Failure Risk | Recommended Routing Pattern |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **High-Precision Extraction** 9 | Native schema enforcement, zero preamble, strict type adherence.11 | Medium, schema-enforced open-weight or cloud API.11 | First-attempt JSON schema validity rate, extraction recall.10 | Truncated payloads, hallucinated keys, type drift.11 | Direct route to dedicated extraction model with schema validation.13 |
| **Research Synthesis** 1 | Long-context retention, strict citation fidelity, uncertainty calibration.1 | Premium, deep-context model.2 | Citation support accuracy, grounded synthesis score.1 | Lost-in-the-middle context decay, hallucinated facts.1 | Context compilation and retrieval-grounded generation.1 |
| **Tool-Use Agentic Loops** 9 | Dynamic state tracking, resilient recovery, parameter discipline.10 | Premium model or specialized agentic model.3 | First-attempt tool-calling success rate, planning accuracy.10 | Tool misuse loops, malformed payloads, state fragmentation.10 | Pre-generation validation router with immediate retry loop.10 |
| **Mathematical Problem Solving** 2 | Step-by-step cognitive search, self-correction, rigorous validation.2 | Specialized inference-time compute model.4 | Pass@k on specialized math datasets (e.g., AIME).2 | Brittle step execution, arithmetic errors, loop termination failure.2 | Pre-generation diagnostic routing to high-effort processing tier.2 |
| **Production Code Refactoring** 1 | Multi-file context digestion, strict style adherence, contract preservation.1 | High-context developer model.22 | Build-and-test success rate, syntactic validity.1 | Over-engineered code, interface breakages, regression.2 | Routing to specialized coding model at medium effort.2 |
| **Visual Document Intelligence** 3 | Direct spatial mapping, OCR parsing accuracy, tabular layout mapping.3 | Native multimodal model with layout awareness.3 | Visual grounding rate, structure mapping accuracy.3 | Erroneous cellular mapping, bounding box drift, OCR failures.3 | Native multimodal routing with structural parser validation.3 |

### **Cognitive Computation and Reasoning-Depth Fit**

System architects must align the cognitive depth of a model with both the risk profile of the task and the economics of the execution. Production evaluations in 2026 demonstrate that adjusting the reasoning-time compute parameters on modern architectures changes quality, latency, and cost in highly predictable, non-linear ways.2

#### **The Cost-Quality Crossover**

Deploying a model with excessive reasoning-time compute for low-complexity classification is economically inefficient. Conversely, applying a shallow model to complex tasks results in systematic execution failures that require expensive retry routines or human remediation.10  
The relation between reasoning-time computational effort and output quality varies significantly across distinct task domains:

* **Mathematical Domains:** Math-heavy tasks (such as AIME benchmarks) show a steep, highly responsive quality curve. For instance, GPT-5.5 Pro's pass-rate scales from 69.3% at low reasoning effort to 79.3% at medium effort, and reaches 91.7% at high effort.2 This behavior makes high-effort configurations economically viable for math tasks because output correctness is binary and highly critical.2  
* **Software Engineering Domains:** Multi-file refactoring tasks do not show linear benefits at high reasoning efforts. In software engineering benchmarks (e.g., Expert-SWE Refactor), GPT-5.5 Pro peaks at a medium configuration (73.1% pass-rate) and actually regresses to 71.4% at high configurations due to over-engineering, which can violate established test contracts.2 Thus, medium configurations are the optimal default for software systems.2  
* **Analytical and Scientific Domains:** Graduate-level science tasks (such as GPQA Diamond) exhibit a steady upward curve. Performance increases by 12 to 15 percentage points when transitioning from Low to Medium effort, and continues to scale moderately (an additional 3 to 7 percentage points) at high configurations, making medium-to-high configurations the standard for complex analytical pipelines.2

### **Context-Fit and Retrieval Economics**

A model's context window cannot be evaluated solely on its maximum advertised token capacity. System performance is heavily affected by how effectively the model processes information across that window.

#### **Context Stuffing versus Retrieval-Augmented Generation (RAG)**

Architects must mathematically determine when to stuff entire document sets into high-context windows (e.g., Gemini 3 Pro's 10M token window) 25 versus when to build RAG pipelines.  
The cost-benefit analysis of context stuffing is governed by the relation:  
Cost_stuffing = (C_corpus / 1000) * P_input  
where C_corpus is the total corpus token size, and P_input is the price per 1,000 input tokens.8 For a corpus of 400,000 tokens evaluated on a premium model costing $0.005 per 1,000 input tokens, the input cost is $2.00 per query.8  
The cost of a managed RAG query is formulated as:  
Cost_RAG = C_embed + C_search + C_generation  
where C_generation is defined by the top-k retrieved chunks.8 If a RAG pipeline retrieves 5 chunks of 512 tokens each (2,560 tokens), the input generation cost drops to approximately $0.000413, making RAG significantly more cost-effective as query volume increases.8  
RAG pipelines are economically justified when the cost of corpus indexing and vector searching amortizes below the per-query expense of context stuffing. However, when tasks require synthesizing holistic relationships across an entire document set (e.g., legal contract consistency audits), high-context models with stable instruction-hierarchy preservation are technically required regardless of input cost.1

### **Structured-Output and Tool-Use Architecture**

The interface between natural language models and deterministic software engines requires strict output formatting. Production systems suffer from failures at this boundary when models output unparsable JSON, omit required fields, or experience type drift.9

#### **Evolutionary Generations of Structured Output**

* **Generation 1 (Prompting):** Treats format adherence as a soft instruction (e.g., "Respond only in valid JSON"). This approach exhibits a 5% to 20% failure rate under load due to preamble conversational text, hallucinated keys, or truncation.11  
* **Generation 2 (Function/Tool Calling):** Features provider-level fine-tuning where models generate arguments that align with a registered JSON schema. This approach is highly flexible but lacks formal mathematical guarantees.9  
* **Generation 3 (Native Schema-Enforced APIs):** Introduced as OpenAI strict mode or Gemini response schema. These APIs guarantee 100% schema compliance for accepted schemas by masking invalid tokens at each generation step.11 However, they support only a subset of JSON schema specifications (e.g., excluding minLength, maxLength, and complex regex patterns) and require setting additionalProperties: false.11  
* **Generation 4 (Engine-Level Constrained Decoding):** Implemented in self-hosted engines like vLLM. These frameworks modify token probability distributions at runtime using Finite State Machines (FSM) or Pushdown Automata (PDA) based on a compiled Context-Free Grammar (CFG).11

#### **Latency Overheads of Constrained Decoding**

Architects must account for the latency profiles of engine-level structured output generation:

* **FSM Compilers (e.g., Outlines):** Compiling a complex JSON schema into an FSM is highly expensive. While token generation remains fast, schema compilation takes 8 to 60 seconds.11 Pathological schemas with large enum sets can exceed 10 minutes, making cold starts or dynamic schemas a major latency risk.11  
* **PDA Compilers (e.g., XGrammar, llguidance):** PDA-based stack tracking minimizes compilation overhead.11 XGrammar (the default backend in vLLM v0.6+) delivers near-zero compilation latency, while llguidance exhibits a low per-token overhead of only 6 to 9ms, compared to the 15 to 46ms seen in older FSM implementations.11

## **Deployment Fit and Operational Constraints**

A model with strong capability metrics is unusable if it does not fit the system's operational constraints. Architects must evaluate the latency, throughput, scaling, security, and hardware burdens of different deployment configurations.

### **Deployment Fit Matrix**

The choice of deployment topology is a trade-off between control, infrastructure overhead, and runtime efficiency.

| Metric | Managed API | Hosted Open Model | Self-Hosted Instance | Local Workstation/Edge | Hybrid Portfolio |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **P50 Latency** | Low (0.73s - 1.9s).25 | Low (0.5s - 1.2s). | Ultra-low (optimized vLLM scheduler).5 | Variable (5x - 30x slower if CPU offloaded).7 | Variable (governed by orchestrator overhead).14 |
| **Throughput Scaling** | Infinite (managed by provider rate limits). | High (auto-scaling node clusters). | Constrained by local GPU resource availability.6 | Single-concurrency bound (VRAM limited).7 | Dynamic (routes simple tasks to elastic tiers).14 |
| **Data Privacy** | Subject to provider data-use policies.2 | High (runs inside private cloud VPC). | Absolute (fully air-gapped deployments). | Absolute (local storage and computation).7 | Variable (requires strict regional routing rules). |
| **Hardware Burden** | Zero (fully outsourced). | Low (provisioned as SaaS container). | Very High (requires bare-metal GPU clusters).6 | Workstation hardware setup cost ($8.5k GPU cost).7 | High (requires managing API keys and GPU nodes). |
| **Observability** | Restricted to provider API telemetry. | Medium (limited to serving envelope). | Complete (direct access to logit distributions). | Complete (local diagnostic access). | Fragmented (demands unified routing traces). |
| **Total Cost of Ownership** | High at scale (linear per-token pricing).27 | Medium (provisioned infrastructure cost). | High CAPEX, highly efficient at high continuous load.5 | Low CAPEX (one-time workstation purchase).7 | Optimized (minimizes premium execution fees).14 |
| **Vendor Lock-in** | High (proprietary API models). | Low (migratable to any cloud host). | Zero (weights run on standard hardware).23 | Zero (runs on consumer or workstation silicon).7 | Low (modular integration of providers). |

### **Physical GPU Arithmetic and Memory Profiling**

Running open-weight or self-hosted models (e.g., Llama 3.3 70B, DeepSeek V4) 22 requires precise physical VRAM mapping to prevent out-of-memory (OOM) crashes or slow CPU offloading.7

#### **VRAM Allocation Formula**

The total physical VRAM required to serve a model at inference is formulated as:  
V_total approx (P * B_param) * 1.18 + V_kv  
where P is the parameter count in billions, B_param is the precision footprint in bytes per parameter (2 for FP16, 1 for FP8, 0.5 for INT4), 1.18 represents an 18% safety margin for activations and framework overhead, and V_kv is the memory allocated to the KV cache pool.6

#### **Mixture-of-Experts (MoE) VRAM Trap**

In MoE architectures, the active parameter count (which dictates inference speed) is significantly smaller than the total parameter count.6 However, **all parameters must be loaded into VRAM** to execute inference.6 For example, DeepSeek R1 has 671B total parameters and activates 37B per token.7 At INT4 quantization (0.5 bytes/parameter), the weights alone require:  
V_weights = (671 * 0.5) * 1.18 approx 395.89 GB of VRAM  
This requirement pushes MoE models out of workstation reach and requires multi-GPU datacenter clusters, despite their fast active token generation.7

#### **KV Cache VRAM Overhead**

The memory footprint of the KV cache increases linearly with context length and batch size:  
V_kv approx 2 * N_layers * N_heads * D_head * L_context * N_batch * B_element  
For Llama 3.3 70B (80 layers, 8 KV heads, 128 head dimension) running at BF16 (B_element = 2):  
V_kv_per_1k = 2 * 80 * 8 * 128 * 1024 * 1 * 2 = 335,544,320 Bytes approx 320 MB per concurrent 1K context  
At 128K context with 8 concurrent requests, the KV cache footprint exceeds 320 GB, often dwarfing the base model weight footprint.6 Architects using vLLM configure this via --gpu-memory-utilization (typically 0.90 to 0.95 on bare-metal instances) and adjust --max-model-len to prevent memory fragmentation and ensure scheduling stability.5

### **Legal Compliance and License Constraints**

Model selection must be legally compliant. Open-weight models are governed by custom community licenses that restrict their usage.

#### **Llama 3.3 Community License Agreement Analysis**

Meta's Llama 3.3 community license allows commercial use but contains several strict conditions 17:

* **Litigation Trigger:** If an organization initiates intellectual property litigation against Meta, the license is immediately terminated.17  
* **Acceptable Use Policy (AUP):** The license prohibits using the model for unlicensed professional practices (such as financial, legal, or medical operations).17  
* **Monthly Active User (MAU) Scale Limit:** Organizations with more than 700 million active users must request a custom commercial license from Meta.  
* **Non-OSI Compliance:** Because of these restrictive usage conditions, the Open Source Initiative (OSI) does not classify Llama licenses as true open source, categorizing them instead as "open-weight" commercial licenses.19

### **Governance and License Fit Matrix**

| Model | License Type | Commercial Restrictions | Output Data Use Constraints | Audit Controls | Provider Data Retention |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Llama 3.3** 17 | Custom Community | Permissive; limited at 700M MAU and prohibited in unlicensed professional practices.17 | None; permits downstream fine-tuning of competing models. | None. | Zero if locally hosted.22 |
| **DeepSeek V4** 23 | MIT | None; fully open commercial use.23 | None. | None. | Zero if locally hosted.23 |
| **Mistral Large** 22 | Mistral Research / Commercial | Restrictive on free tier; requires commercial agreements for production serving. | Prohibits competitive model distillation. | None. | Zero if locally hosted.22 |
| **Qwen 2.5** 22 | Apache 2.0 / Custom | Permissive commercial use. | None. | None. | Zero if locally hosted.22 |
| **GPT-5.4** 2 | Proprietary API | Restrained by API terms of service. | Strictly prohibits using outputs to train competitive models. | High; provider logs transactions for policy compliance. | Typically 30 days unless Enterprise zero-retention is signed.2 |

## **Failure Tolerance and Risk Fit**

Every model will eventually fail. A robust architecture must proactively categorize failures, establish detection methods, and design recovery paths.

### **Failure Tolerance Profile**

This profile outlines common model failures, indexing them by severity, detection complexity, recovery, and mitigation.

| Failure Mode | Severity | Detectability | Recoverability | Acceptable Contexts | Unacceptable Contexts | Mitigation Path |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Preamble Contamination** 11 | Low | Very High | Automated | Creative ideation, unstructured search.1 | Automated schema parsers.9 | Strip non-JSON prefixes with regex.11 |
| **Malformed JSON** 9 | High | High | Automated | High-tolerance logging systems. | API-integrated applications.9 | PDA constrained decoding masks.11 |
| **Tool argument mismatch** 10 | Critical | High | Semichannel | Exploratory sandbox trials. | Production database write transactions.9 | Schema verification before execution.9 |
| **Refusal Error** 13 | High | High | Manual | Highly aligned internal checks. | General customer support interfaces. | Prompt tuning and system message refinement.13 |
| **Silent Deduction Drift** 2 | Critical | Low | Manual | Brainstorming sessions. | Medical diagnostics or financial audits. | Multi-model consensus loops.2 |
| **Citation Hallucination** 1 | High | Medium | Manual | Generic text summarization. | Legal drafting or policy QA.1 | Character-span verification filters. |
| **Prompt Injection** 1 | Critical | Medium | Manual | Single-tenant applications. | Multi-tenant customer-facing bots. | Dedicated input-output safety classifiers. |

### **Fail-Open versus Fail-Closed Strategy**

Architectures must define a fallback strategy for every failure boundary:

* **Fail-Open (Optimistic):** Applied in low-risk contexts (such as creative brainstorming or content translation) where fluent, continuous generation is preferred over strict accuracy.1 When a validation check fails, the system logs the error but continues executing, relying on the user to catch mistakes.  
* **Fail-Closed (Pessimistic):** Applied in high-risk contexts (such as financial auditing, healthcare documentation, or legal analysis) where incorrect outputs are unacceptable.1 When the system detects a failure (e.g., a schema mismatch, low confidence score, or ungrounded claim), it halts execution, rejects the output, and escalates to a human review queue.2

## **Portfolio Architecture, Routing, and Economics**

Highly optimized production systems rarely rely on a single model. Instead, they use coordinated portfolios of specialized models to optimize accuracy, latency, and cost.

### **Model Portfolio and Routing Map**

This architecture maps tasks across a distributed portfolio, routing queries dynamically based on difficulty, risk, and structural needs.

```
+----------------------------------------------------------------------------------------------------+
|                              MODEL PORTFOLIO AND ROUTING MAP                                       |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    
|  Goal: route each request to the cheapest model that can satisfy capability, latency,              
|  governance, and failure-tolerance requirements without creating avoidable retries.                
|                                                                                                    
|  [ Incoming Request ]                                                                              
|        |                                                                                           
|        v                                                                                           
|  +------------------------------------------------------------------------------------------+      
|  |                              Task Profile Interpreter                                    |      
|  |                                                                                          |      
|  |  Identify: task class | risk level | modality | context length | schema needs            |      
|  |            tool-use complexity | latency SLA | cost ceiling | privacy constraints        |      
|  +---------------------------------------------+--------------------------------------------+      
|                                                |                                                   
|                                                v                                                   
|  +------------------------------------------------------------------------------------------+      
|  |                              Pre-Generation Diagnostic Router                            |      
|  |                                                                                          |      
|  |  Decide route before expensive generation whenever possible.                             |      
|  |                                                                                          |      
|  |  Signals: semantic difficulty | required capability | failure tolerance | budget fit     |      
|  |           deployment fit | data-residency fit | workload class                           |      
|  +----------------------+----------------------+----------------------+---------------------+      
|                         |                      |                      |                            
|                         v                      v                      v                            
|          +-------------------------+  +-----------------------+  +-----------------------------+   
|          | Economy Route           |  | Premium Route         |  | Specialist Route            |   
|          |                         |  |                       |  |                             |   
|          | low-risk classification |  | research synthesis    |  | code / math / multimodal    |   
|          | extraction              |  | complex reasoning     |  | structured output / tools   |   
|          | simple drafting         |  | high-risk generation  |  | embedding / reranking       |   
|          +-----------+-------------+  +-----------+-----------+  +-------------+---------------+   
|                      |                            |                            |                   
|                      +----------------------------+----------------------------+                   
|                                                   |                                                
|                                                   v                                                
|  +------------------------------------------------------------------------------------------+      
|  |                              First-Pass Execution                                        |      
|  |                                                                                          |      
|  |  Execute selected route with its assigned model and effort tier.                         |      
|  +---------------------------------------------+--------------------------------------------+      
|                                                |                                                   
|                                                v                                                   
|  +------------------------------------------------------------------------------------------+      
|  |                              Validation Gate                                             |      
|  |                                                                                          |      
|  |  Check: schema validity | tool arguments | citation grounding | confidence signals       |      
|  |         refusal behavior | policy compliance | semantic adequacy                         |      
|  +---------------------------------------------+--------------------------------------------+      
|                                                |                                                   
|                                      [ Validation Pass? ]                                          
|                                         /                 \                                        
|                                  Yes   /                   \   No                                  
|                                       v                     v                                      
|  +-----------------------------------------+   +--------------------------------------------+      
|  | Return Valid Response                   |   | Failure Classifier                         |      
|  | with trace, route ID, and model ID      |   |                                            |      
|  +--------------------+--------------------+   | schema failure | low confidence            |      
|                       |                        | semantic failure | tool error              |      
|                       |                        | policy issue     | unsupported modality    |      
|                       |                        +------------------+-------------------------+      
|                       |                                           |                                
|                       |                                           v                                
|                       |                        +--------------------------------------------+      
|                       |                        | Recovery Policy                            |      
|                       |                        |                                            |      
|                       |                        | fail-open  -> log and continue if low-risk |      
|                       |                        | fail-closed -> escalate if high-risk       |      
|                       |                        +------------------+-------------------------+      
|                       |                                           |                                
|                       |                              +------------+-------------+                  
|                       |                              |                          |                  
|                       |                              v                          v                  
|                       |                 [ Stronger Model Retry ]      [ Human Review Queue ]       
|                       |                              |                          |                  
|                       |                              v                          v                  
|                       |                 [ Re-validate output ]      [ Fail-Closed Resolution ]     
|                       |                              |                           |                 
|                       +------------------------------+---------------------------+                 
|                                                      |                                             
|                                                      v                                             
|  +------------------------------------------------------------------------------------------+      
|  |                              Telemetry and Economics Loop                                |      
|  |                                                                                          |      
|  |  Track: route hit rate | escalation rate | cost per success | latency | failure mode     |      
|  |         schema adherence | tool success | human escalation frequency                     |      
|  |                                                                                          |      
|  |  Feed results back into routing thresholds, portfolio design, and MDR updates.           |      
|  +------------------------------------------------------------------------------------------+      
|                                                                                                    
+----------------------------------------------------------------------------------------------------+
| Doctrine: route before generation when possible, validate after generation always, and only        |
| cascade when the failure rate is low enough to beat premium-direct economics.                      |
+----------------------------------------------------------------------------------------------------+
```

### **Cascade Optimization and Routing Economics**

System economics in 2026 are defined by the total cost per successful outcome rather than sticker price per token.2 Architects must analyze routing policies using structured economic formulas.

#### **Cascade Routing Math**

A model cascade routes an incoming query first to a cheap, low-capacity model (L), evaluates the model's confidence s_L, and escalates to a premium model (H) only if s_L falls below a threshold tau.14  
The expected cost of a two-model cascade is formulated as:  
E[C] = C_L + P(s_L < tau) * C_H  
where C_L is the cost of the cheap model, C_H is the cost of the premium model, and P(s_L < tau) is the probability of escalation.14  
The expected system quality is:  
E[Q] = P(s_L >= tau) * Q_L(s_L >= tau) + P(s_L < tau) * Q_H(s_L < tau)  
Model cascades are limited primarily by **structural cost**: the system must pay the cheap model's prefill and generation costs before making any escalation decision.14 If the escalation rate is high, the total cost can exceed the price of routing directly to the premium model.14

#### **Pre-Generation Diagnostic Routing**

To bypass the structural costs of cascades, architects deploy semantic routers (e.g., AMRO-S, which uses a supervised fine-tuned small language model).28 This router evaluates the query's intent *before* any model execution, routing complex questions directly to the premium model.14

#### **Speculative Decoding as a Latency Optimization**

Speculative decoding is a latency optimization that accelerates inference without changing the target model's output distribution.29

* **How it works:** A small draft model (e.g., Llama 3.2 1B) 30 rapidly proposes k candidate tokens, which are verified in parallel by the target model (e.g., Llama 3.3 70B) in a single forward pass.6  
* **Drafter Training (LK Losses):** Rather than traditional KL divergence training (which covers multiple modes and degrades draft accuracy), modern draft models are trained using Total Variation (TV) minimization or LK losses.32 This approach directly maximizes the token acceptance rate alpha 32, where:

alpha = 1 - TV(p, q)

* **The Concurrency Trap:** Speculative decoding is highly effective when the server is memory-bandwidth-bound (typically batch size < 4 to 8), reducing latency by up to 3x.24 However, as concurrent batch size scales to 16 or 32, the GPU becomes compute-bound.26 The verification overhead of evaluating candidate tokens then consumes the latency savings, resulting in a 5% to 10% performance regression in high-traffic production environments.26

### **Routing Economics Framework**

This framework compares routing protocols across critical performance and economic dimensions.

| Routing Protocol | Cost | Latency | Quality | Risk | Cacheability | Retry Behavior | Cost per Success |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Direct Route (Premium)** | High | Low | Maximum | Low | High | Minimal | Predictable |
| **Model Cascade** 14 | Variable | Multi-stage | Balanced | Low | Low | Structural | High if escalated.14 |
| **Diagnostic Router** 14 | Low | Unified | High | Medium | High | Isolated | Highly optimized.14 |
| **Speculative Routing** | High | Ultra-low | High | Low | High | Normal | Low (bandwidth-bound).26 |
| **Human Escalation** 2 | Extreme | High | Absolute | None | None | Manual | High CAPEX burden.2 |

## **Evaluation-Driven Selection**

Static leaderboards provide initial candidate signals, but the final model selection must be decided by empirical testing on the system's actual workload.1

### **Model Selection Evaluation Harness**

Architects must build a comprehensive, automated evaluation harness that runs candidate models through a representative, decontaminated test suite.

| Harness Component | Test Type | Target Metric | Production Target |
| :---- | :---- | :---- | :---- |
| **Golden Sets** 13 | Regression Testing | Absolute Accuracy | Match baseline within +/- 0.5%. |
| **Adversarial Set** 2 | Robustness check | Refusal/Jailbreak Rate | Zero safety failures. |
| **Needle-in-a-Haystack** 8 | Retrieval Validation | Context Recall | >99% recall across the active window.8 |
| **Schema Test** 13 | Constraint check | Syntactic Validity | 100% validation compliance.11 |
| **Tool Simulation** 10 | Multi-agent execution | Trace Integrity | First-attempt success >90%.10 |
| **Multilingual Sweep** 17 | Dialect evaluation | Translation Quality | BLEU score maintenance.17 |
| **Shadow Telemetry** 2 | Parallel processing | Traffic Distribution | Match offline latency predictions.26 |

### **Benchmark Interpretation Guide**

Public benchmarks provide initial signal but are subject to structural limitations. Architects must evaluate them using specific guidelines.

#### **Contamination, Saturated Ceilings, and the Task ID Flaw**

Static knowledge tests (such as MMLU or MMLU-Pro) have largely saturated, with leading models clustering in a narrow 88% to 94% band where differences are mostly statistical noise.2  
Furthermore, static benchmarks are highly susceptible to **training set contamination**, where models memorize answers rather than demonstrate deductive capabilities.1 For example, audits of SWE-bench Verified (a subset of GitHub software issues) revealed that models could reproduce the correct code patches verbatim using only the task ID, showing that the model was retrieving the answer from memory rather than debugging.2  
To counter this, architects must prioritize dynamic, continuously updated benchmarks (such as SWE-ReBench or LiveBench) that source problems post-dating the models' training cutoff dates.2

#### **Harness Multipliers and the Verification Gap**

In agentic benchmarks, the scaffold or harness (the code allowing the model to run files and execute tests) can swing scores by **10 to 20 percentage points** on the exact same model weights.2 For example, Claude Opus 4.5 achieves an impressive 80.9% score on SWE-bench Verified but drops to 45.9% on SWE-bench Pro—a 35-point collapse on the same weights when evaluating multi-file edits and longer contexts.2

#### **Random Matrix Theory and Dimensional Redundancy**

Applying Random Matrix Theory (RMT) to the evaluation landscape shows that public benchmarks are highly redundant.12 For example, the 43 sub-tasks of the Open LLM Leaderboard compress down to an Effective Dimensionality (ED) of just 4.5, meaning the benchmark measures only a few distinct axes of capability.12  
Furthermore, benchmarks can exhibit conditional negative correlations:  
rho(MATH x MuSR) = -0.635  
rho(GPQA x MATH) = -0.340  
This indicates that models optimized to maximize scores on one specific capability (like mathematical deduction) can show regressions in other areas (such as multi-step spatial reasoning), proving that there is no single "best" model for all workloads.1

### **Benchmark Performance Guide**

| Benchmark | Target Capability | Saturated Ceiling | Production Gap | Harness Dependency |
| :---- | :---- | :---- | :---- | :---- |
| **MMLU / MMLU-Pro** 16 | General knowledge | Saturated (>90%).16 | Low correlation to narrow domains.1 | Low; straightforward multi-choice. |
| **GPQA Diamond** 16 | Scientific deduction | High (>94%).2 | Fails to measure layout comprehension.3 | Low; multiple-choice extraction. |
| **HLE (Human Exam)** 16 | Advanced deduction | Low (<55%).16 | Early stages; limited domain coverage.16 | Low; short-answer parsing.2 |
| **SWE-bench Verified** 2 | Repository coding | Saturated (>85%). | High risk of task-ID contamination.2 | High; agent scaffolding swings score.2 |
| **SWE-bench Pro** 2 | Multi-file development | Active (<65%).2 | Best simulation of software engineering.2 | Extreme; harness controls context.2 |
| **Terminal-Bench 2.0** 2 | CLI command control | Active (<70%).2 | Excellent command execution proxy.2 | High; requires active terminal host.2 |

## **Doctrinal Artifacts and Architecture Standards**

System choices must be formally documented to ensure long-term traceablity, compliance, and regression management.

### **Model Decision Record (MDR) Template**

Architects must complete this standardized record for every production model transition:

# **Model Decision Record (MDR):**

```
## **1. Context and Problem Statement**

* Describe the specific task graph node and its cognitive requirements.  
* Detail the system constraints (latency SLAs, cost targets, privacy requirements).

## **2. Selected Model and Configuration**

* Selected Model Identifier:  
* Deployment Topology:  
* Core Parameters:  
  * --gpu-memory-utilization: [e.g., 0.90]  
  * --max-model-len: [e.g., 32768]  
  * --enable-chunked-prefill: [e.g., true]

## **3. Evaluation Evidence**

* Golden Set Accuracy Score: [e.g., 84.2%]  
* Structured-Output Validity Rate: [e.g., 100% via XGrammar]  
* Target Latency P95: [e.g., 820ms]  
* Benchmark References:

## **4. Rejected Alternatives and Rationale**

* Alternative A:  
  * Rejection Reason: Exceeded cost boundaries and violated regional data residency rules.  
* Alternative B:  
  * Rejection Reason: Insufficient instruction following on nested schemas.

## **5. Failure Tolerance and Risk Mitigation**

* Anticipated Failure: Malformed JSON output.  
  * Mitigation: Engine-level PDA constrained decoding mask.  
* Anticipated Failure: Silent extraction omission.  
  * Mitigation: Secondary evaluation schema parsing with fail-closed human escalation.

## **6. Execution Economics**

* Estimated Prefill Cost (per 1M queries): [e.g., $1.20]  
* Estimated Generation Cost (per 1M queries): [e.g., $2.40]  
* Estimated Total Cost Per Successful Outcome: [e.g., $0.0036]

## **7. Lifecycle and Rollout Plan**

* Rollout Strategy: Shadow route 1% of live traffic for 72 hours, scaling to 10% canary.  
* Rollback Trigger: Error rate > 0.5%, P95 latency > 1.2s, or security injection detection.  
* Reconsideration Conditions: Release of decontaminated open-weight models in the same size class.
```

### **Selection Failure Modes and Anti-Patterns**

* **Leaderboard Shopping:** Selecting a model based solely on headline scores on saturated, contaminated benchmarks (e.g., MMLU), ignoring task-specific performance and deployment constraints.1  
* **The Single Model Monolith:** Forcing one general-purpose model to execute every node in a complex task graph, leading to high latencies and excessive costs.1  
* **The Speculative Concurrency Trap:** Enabling speculative decoding in high-throughput production environments (batch size > 16 without verifying if the GPU has transitioned to a compute-bound state, resulting in performance regressions.26  
* **Unverified Long-Context Stuffing:** Assuming a model's long-context window maintains high retrieval accuracy near the middle of the window without running needle-in-a-haystack or citation tests.1  
* **FSM Cold-Start Latency:** Deploying Outlines-style FSM schemas in latency-sensitive APIs without pre-compiling and caching the target schema, causing latency spikes.11  
* **Unintentional Tokenizer Drift:** Swapping models without verifying if the new tokenizer maps the same input text to a larger number of tokens, which can increase nominal token costs by 10% to 35% under the same pricing tier.2

### **Evaluation and Observability Guidance**

To maintain system margins and detect performance drift, production systems must continuously monitor these operational metrics:

* **Task Success Rate:** The percentage of model completions that successfully complete the downstream workflow without requiring retries or human intervention.15  
* **First-Attempt Schema Adherence:** The rate at which the raw model output matches the targeted JSON schema, verifying the efficiency of schema enforcement.10  
* **Cost Per Successful Outcome:** The total cost of execution—including prefill, generation, caching, retries, and human validation—divided by the rate of valid outputs.5  
* **TTFT (Time-to-First-Token) Distribution:** Latency tracking (P50, P90, P99) of the model's initial response time.5  
* **Inter-Token Latency:** The average generation time per token, tracking server load and scheduler efficiency.24  
* **Citation Grounding Score:** The percentage of output claims that are directly supported by verifiable character-spans in the source documents.1  
* **Refusal and Escalation Rate:** The frequency with which the model refuses requests or escalates queries to human review.2  
* **Tokenizer Compression Ratio:** The ratio of text characters to generated tokens, tracking tokenizer efficiency.2

### **Cross-Canon Handoff Map**

Model selection does not exist in isolation. It serves as the bridge between model training, adaptation, serving, and system orchestration.

```
+------------------------------------------------------------------------------------------------+
|                                CROSS-CANON HANDOFF MAP                                         |
+------------------------------------------------------------------------------------------------+
|                                                                                                
|                     +------------------------------------------------------+                   
|                     | AI-ENG-G: MODEL SELECTION (THIS REPORT)              |                   
|                     | capability fit | deployment fit | failure tolerance  |                   
|                     | routing doctrine | portfolio design | MDR evidence   |                  
|                     +-------------------------------+----------------------+                   
|                                                     |                                          
|          +------------------------------------------+---------------------------------------+  
|          |                                          |                                       |  
|          v                                          v                                       v  
|  +-------------------------------+      +-------------------------------+      +-------------------------------+
|  | AI-ENG-H: MODEL ADAPTATION    |      | AI-ENG-I: LIFECYCLE CONTROL   |      | AI-ENG-J / K / L: RUNTIME     |
|  | fine-tuning | LoRA |          |      | registries | canaries |       |      | throughput | memory |         |
|  | distillation decisions        |      | rollback / promotion logic    |      | serving topology | routing    |
|  +---------------+---------------+      +---------------+---------------+      +---------------+---------------+
|                  |                                      |                                      |
|                  |                                      |                                      |
|                  v                                      v                                      v
|  +-------------------------------+      +-------------------------------+      +-------------------------------+
|  | AI-ENG-M: AGENTIC             |      | AI-ENG-N: TOOL CONTRACTS      |      | AI-ENG-W: FALLBACK CHAINS     |
|  | ORCHESTRATION                 |      | schemas | argument structure  |      | retries | recovery paths |    |
|  | task-model assignment         |      | tool-use reliability          |      | human escalation              |
|  +---------------+---------------+      +---------------+---------------+      +---------------+---------------+
|                  \                                      |                                      /
|                   \                                     |                                     /
|                    \                                    |                                    /
|                     \                                   |                                   /
|                      \                                  |                                  /
|                       +---------------------------------+---------------------------------+
|                                                         |
|                                                         v
|                                        +----------------------------------+
|                                        | AI-ENG-Z: TELEMETRY              |
|                                        | evals | observability | drift    |
|                                        | cost per success | routing traces|
|                                        +----------------------------------+
|                                                                                                
+------------------------------------------------------------------------------------------------+
| Handoff doctrine: model selection is the decision layer that exports deployment choices,       |
| routing policy, risk assumptions, MDR evidence, and operating targets to adaptation, lifecycle,|
| serving, tooling, fallback, and observability systems.                                         |
+------------------------------------------------------------------------------------------------+
```

| Downstream Canon Report | Ownership Intersection | Technical Input | Functional Dependency |
| :---- | :---- | :---- | :---- |
| **AI-ENG-H: Adaptation** | Capability alignment | Selected base model weights.22 | Defines if adaptation (fine-tuning, LoRA) is required to close gaps.22 |
| **AI-ENG-I: Lifecycle** | Transition management | Model Decision Record (MDR). | Establishes registry metadata, rollout speeds, and rollback triggers.2 |
| **AI-ENG-J/K/L: Runtime** | Inference execution | Serviced parameter configurations.6 | Controls KV cache size, continuous batching, and quantization.5 |
| **AI-ENG-M: Agentic** | Workflow orchestration | Task-to-Model Fit assignments.4 | Directs tool-use state loops and multi-agent coordination costs.4 |
| **AI-ENG-N: Tools** | Interface definition | Output schema configuration.9 | Governs function calling structures and argument parsing rules.9 |
| **AI-ENG-W: Fallbacks** | Resilience design | Failure Tolerance Profile.13 | Establishes the fallback path rules and human-in-the-loop triggers.2 |
| **AI-ENG-Z: Telemetry** | Observation monitoring | Selected performance targets.10 | Defines logging protocols, prompt caching ratios, and incident metrics.27 |

## **Durable Principles of Model Selection**

This report establishes five core, durable principles for model selection:

1. **Selection Over Ranking:** Never choose a model based on general leaderboard rankings. Always select models based on empirical validation against the system's specific task profile, latency SLAs, cost margins, and regulatory requirements.1  
2. **Physical Constraints Are Absolute:** Model capabilities are irrelevant if the model cannot run on target hardware. VRAM mapping, KV cache sizing, and serving concurrency limits must be mathematically verified before deployment.6  
3. **Active versus Total Memory Integrity:** In Mixture-of-Experts (MoE) architectures, active parameters dictate generation speed, but total parameters dictate the VRAM footprint. Architects must never confuse active token generation with actual physical memory requirements.6  
4. **Structure Before Inference:** Never rely on prompting alone to ensure structured output or tool compliance. Always implement native schema-enforced APIs or engine-level constrained decoding to guarantee format adherence.11  
5. **Design for Failure:** Every model will eventually fail. A robust architecture must define fail-open or fail-closed recovery paths and implement automated validation layers to catch errors before they propagate downstream.10

#### **Works cited**

1. Model Ranking vs Model Selection: Why LLM Leaderboards Don't Pick the Right Model for Production | Trismik Blog, accessed June 7, 2026, [https://blog.trismik.com/model-ranking-vs-model-selection/](https://blog.trismik.com/model-ranking-vs-model-selection/)  
2. LLM Benchmark Methodology 2026: Reading Leaderboards, accessed June 7, 2026, [https://www.digitalapplied.com/blog/llm-benchmark-methodology-2026-contamination-leaderboard-guide](https://www.digitalapplied.com/blog/llm-benchmark-methodology-2026-contamination-leaderboard-guide)  
3. AI model benchmarks 2026: GPT, Claude, Gemini compared - Logic, accessed June 7, 2026, [https://logic.inc/resources/ai-model-benchmarks-guide](https://logic.inc/resources/ai-model-benchmarks-guide)  
4. The Open-Source AI Revolution: How DeepSeek, OpenClaw, and Open-Weight Models Are Reshaping AI in 2026 | AI Magicx Blog, accessed June 7, 2026, [https://www.aimagicx.com/blog/open-source-ai-revolution-deepseek-openclaw-2026](https://www.aimagicx.com/blog/open-source-ai-revolution-deepseek-openclaw-2026)  
5. LLM Serving Optimization: Continuous Batching, PagedAttention, and Chunked Prefill on H100 (2026) | Spheron Blog, accessed June 7, 2026, [https://www.spheron.network/blog/llm-serving-optimization-continuous-batching-paged-attention/](https://www.spheron.network/blog/llm-serving-optimization-continuous-batching-paged-attention/)  
6. GPU Requirements 2026: Llama 4 = 1× H100 ($2.50/hr), DeepSeek V3.2 = 8× H200 ($36/hr), Qwen 3.5 27B = 1× H100 | Spheron Blog, accessed June 7, 2026, [https://www.spheron.network/blog/gpu-requirements-cheat-sheet-2026/](https://www.spheron.network/blog/gpu-requirements-cheat-sheet-2026/)  
7. Local or Cloud AI? The Real Math Nobody's Doing - Byrnu, accessed June 7, 2026, [https://byrnu.com/en/blog/local-vs-cloud-ai](https://byrnu.com/en/blog/local-vs-cloud-ai)  
8. Home - RTrentin's world, accessed June 7, 2026, [https://rtrentinsworld.com/home/](https://rtrentinsworld.com/home/)  
9. JSON Schema (AI) - Guild.ai, accessed June 7, 2026, [https://www.guild.ai/glossary/json-schema-ai](https://www.guild.ai/glossary/json-schema-ai)  
10. ATLAS-RTC: Closing the Loop on LLM Agent Output with Token-Level Runtime Control, accessed June 7, 2026, [https://arxiv.org/html/2603.27905v2](https://arxiv.org/html/2603.27905v2)  
11. Beyond JSON Mode: Getting Reliable Structured Outputs from LLMs ..., accessed June 7, 2026, [https://tianpan.co/blog/2025-10-29-structured-outputs-llm-production](https://tianpan.co/blog/2025-10-29-structured-outputs-llm-production)  
12. BenchScope: How Many Independent Signals Does Your Benchmark Provide? - arXiv, accessed June 7, 2026, [https://arxiv.org/html/2603.29357v1](https://arxiv.org/html/2603.29357v1)  
13. Structured outputs guide: JSON Schema, OpenAI, Claude, Gemini - Logic, accessed June 7, 2026, [https://logic.inc/resources/structured-outputs-guide](https://logic.inc/resources/structured-outputs-guide)  
14. Is Escalation Worth It? A Decision-Theoretic Characterization of LLM Cascades - arXiv, accessed June 7, 2026, [https://arxiv.org/html/2605.06350v1](https://arxiv.org/html/2605.06350v1)  
15. Dynamic Model Routing and Cascading for Efficient LLM Inference: A Survey - arXiv, accessed June 7, 2026, [https://arxiv.org/html/2603.04445v2](https://arxiv.org/html/2603.04445v2)  
16. LLM Benchmarks 2026: Which Model for Which Job - DataVLab, accessed June 7, 2026, [https://datavlab.ai/post/llm-benchmarks-2026-which-model-for-which-job](https://datavlab.ai/post/llm-benchmarks-2026-which-model-for-which-job)  
17. meta-llama/Llama-3.3-70B-Instruct - Hugging Face, accessed June 7, 2026, [https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct)  
18. meta-llama/llama-models: Utilities intended for use with Llama models. - GitHub, accessed June 7, 2026, [https://github.com/meta-llama/llama-models](https://github.com/meta-llama/llama-models)  
19. Llama (language model) - Wikipedia, accessed June 7, 2026, [https://en.wikipedia.org/wiki/Llama_(language_model)](https://en.wikipedia.org/wiki/Llama_(language_model)  
20. (PDF) AgenticAKM : Enroute to Agentic Architecture Knowledge Management - ResearchGate, accessed June 7, 2026, [https://www.researchgate.net/publication/400459554_AgenticAKM_Enroute_to_Agentic_Architecture_Knowledge_Management](https://www.researchgate.net/publication/400459554_AgenticAKM_Enroute_to_Agentic_Architecture_Knowledge_Management)  
21. Can LLMs Generate Architectural Design Decisions? - An Exploratory Empirical study, accessed June 7, 2026, [https://arxiv.org/html/2403.01709v1](https://arxiv.org/html/2403.01709v1)  
22. Which Open-Source LLM Models Are Currently the Best? - GMI Cloud, accessed June 7, 2026, [https://www.gmicloud.ai/en/blog/which-open-source-llm-models-are-currently](https://www.gmicloud.ai/en/blog/which-open-source-llm-models-are-currently)  
23. What Is DeepSeek V4? Open-Weight AI at Frontier-Level Performance | MindStudio, accessed June 7, 2026, [https://www.mindstudio.ai/blog/what-is-deepseek-v4](https://www.mindstudio.ai/blog/what-is-deepseek-v4)  
24. Accelerating decode-heavy LLM inference with speculative decoding on AWS Trainium and vLLM | Artificial Intelligence, accessed June 7, 2026, [https://aws.amazon.com/blogs/machine-learning/accelerating-decode-heavy-llm-inference-with-speculative-decoding-on-aws-trainium-and-vllm/](https://aws.amazon.com/blogs/machine-learning/accelerating-decode-heavy-llm-inference-with-speculative-decoding-on-aws-trainium-and-vllm/)  
25. LLM Leaderboard 2026 — Compare Top AI Models - Vellum, accessed June 7, 2026, [https://www.vellum.ai/llm-leaderboard](https://www.vellum.ai/llm-leaderboard)  
26. Speculative Decoding in Production: Free Tokens and Hidden Traps - TianPan.co, accessed June 7, 2026, [https://tianpan.co/blog/2026-04-17-speculative-decoding-production-hidden-traps](https://tianpan.co/blog/2026-04-17-speculative-decoding-production-hidden-traps)  
27. DeepSeek's Low Inference Cost Explained: MoE & Strategy | IntuitionLabs, accessed June 7, 2026, [https://intuitionlabs.ai/articles/deepseek-inference-cost-explained](https://intuitionlabs.ai/articles/deepseek-inference-cost-explained)  
28. Daily Papers - Hugging Face, accessed June 7, 2026, [https://huggingface.co/papers?q=selective%20routing%20mechanism](https://huggingface.co/papers?q=selective+routing+mechanism)  
29. Speculative decoding: How it works, when it helps & where it fits in your inference stack, accessed June 7, 2026, [https://redis.io/blog/speculative-decoding-llm/](https://redis.io/blog/speculative-decoding-llm/)  
30. PARD: Accelerating LLM Inference with Low‑Cost PARallel Draft Model Adaptation - arXiv, accessed June 7, 2026, [https://arxiv.org/html/2504.18583v4](https://arxiv.org/html/2504.18583v4)  
31. An Interpretable Latency Model for Speculative Decoding in LLM Serving - arXiv, accessed June 7, 2026, [https://arxiv.org/html/2605.15051v1](https://arxiv.org/html/2605.15051v1)  
32. LK losses: Training speculative decoding draft models to directly maximize acceptance rate, accessed June 7, 2026, [https://nebius.com/blog/posts/lk-losses](https://nebius.com/blog/posts/lk-losses)

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