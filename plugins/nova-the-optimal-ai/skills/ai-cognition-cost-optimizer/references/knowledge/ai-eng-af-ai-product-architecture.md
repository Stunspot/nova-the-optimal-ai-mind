# AI-ENG-AF — AI Product Architecture - Use-Case Selection, Workflow Fit & Value Design

## **1. Doctrinal Foundations and the AI-Shaped Hole Fallacy**

AI product architecture is the engineering and systems discipline of selecting, shaping, rejecting, and structuring artificial intelligence capabilities based on their systemic fit within human workflows. It stands as the architectural gateway before software development begins, establishing the criteria that separate high-yield cognitive automation from expensive, non-deterministic failures.  
Traditional digital product discovery focuses on establishing customer needs, usability, technical feasibility, and business viability.1 AI product architecture, however, must navigate a fundamentally different landscape: the transition from deterministic software—where inputs map reliably to outputs and pass standard quality assurance gates—to probabilistic systems that operate with varying degrees of accuracy and exhibit behavioral drift over time.2 In a traditional software release, shipping a feature allows the team to confirm its status as functional or broken; in an AI-driven architecture, a deployed agent may function correctly in only a portion of execution paths, necessitating continuous validation, feedback loops, and runtime governance to sustain business value.2  
This probabilistic nature gives rise to the **AI-Shaped Hole Fallacy**. This fallacy is the systemic mistake of assuming that because an AI model *can* be integrated into a specific process, the workflow possesses a genuine, valuable, and structurally viable AI-shaped problem. It manifests when product teams start their discovery cycles with the mandate to deploy a specific model class rather than isolating a high-intensity workflow bottleneck, user friction point, or data processing constraint.4  
As Matt Clifford observes, "There is no AI-shaped hole in most organizations".5 While modern frontier models can routinely outperform human experts on theoretical tests and clinical evaluations, the utility of this raw intelligence is constrained by human institutions, entrenched rules, regulatory compliance frameworks, and strict permission barriers.5 Adding unconstrained, probabilistic reasoning into tightly coupled, highly regulated systems introduces high latency, cost, and verification burdens that frequently outweigh the marginal cognitive utility of the model.5  
To diagnose this fallacy early, product architects must dissect the proposed use case against deterministic alternatives, evaluating whether the core bottleneck is a lack of cognitive reasoning or simply a failure of traditional workflow design, database schema, or information architecture.4

### **Doctrinal Governing Principle**

AI product architecture begins by identifying where AI belongs and where it does not. A valid AI use case must have workflow friction, data readiness, user tolerance, evaluation clarity, acceptable risk, cost-to-serve viability, and a value model strong enough to justify probabilistic behavior. The useful question is not "Can we add AI?" but "Is AI the right mechanism for this workflow, for these users, with this data, under this risk, at this cost, with measurable value and a clear definition of success?"

### **AI-Shaped Hole Fallacy Diagnostic**

The diagnostic tool below is designed to isolate and expose instances of the AI-Shaped Hole Fallacy during the initial product discovery phase:

| Symptom | Root Cognitive Cause | Failed Automation Assumption | Deterministic Alternative | Diagnostic Probe |
| :---- | :---- | :---- | :---- | :---- |
| **The Chatbot Anti-Pattern** Users are presented with an open-ended conversational canvas to complete highly structured tasks, resulting in high interaction friction. | Mistaking a model's conversational interface for a natural user workflow.8 | Conversational input is universally more intuitive than structured layouts. | Structured web forms, multi-select filters, relational search syntax, and dynamic templates.8 | Does the user need to converse with their data, or do they simply need a fast, precise way to filter, sort, and display structured fields? |
| **Probabilistic Replacement** A deterministic rules engine or database lookup is replaced by an LLM pipeline, resulting in non-deterministic compliance failures and hallucinations. | Believing that LLMs are drop-in replacements for standard relational database queries or business rules. | Generative models can serve as highly reliable truth engines for exact data retrieval. | Standard SQL queries, structured APIs, rules-based validation engines, and deterministic workflow states.4 | Can this task be represented as a finite set of Boolean conditions, or does it genuinely require semantic context and synthesis of unstructured text? 4 |
| **Verification Debt** The system drafts an artifact in seconds, but requires minutes of manual, line-by-line human verification, resulting in zero net time savings. | Designing for output creation while ignoring the cognitive overhead and liability of output validation.9 | Synthesizing content faster automatically translates to a reduction in total task cycle time. | Structured modular builders, boilerplate components, and rules-based formatting. | Is the cost of validating the probabilistic output higher than the cost of drafting it manually from a structured template? 9 |
| **Unattributed Cost Cascades** The pilot operates at high volume, but the unit economics erode the product's gross margins as model execution costs scale.8 | Ignoring non-deterministic agent loop costs, long context windows, and tool-calling retries during early prototyping.12 | Model call costs scale linearly and remain predictable without active optimization layers.12 | Targeted deterministic automation, local lightweight classifiers, and semantic cache layers.8 | What is the maximum cost-to-serve limit per task, and does the model's non-deterministic execution path fit within that envelope at scale? 12 |
| **The Passive Validation Loop** The user interface fails to capture explicit corrections, allowing model drift and errors to propagate silently into downstream systems. | Treating human-in-the-loop oversight as a passive checkbox rather than an active data collection interface.9 | Human operators will actively catch and correct every subtle semantic error without explicit UI forcing functions.13 | Explicit user confirmation fields, diff rejection tracking, and validation gates.14 | Does the system capture the exact differences between the model's output and the human's final edit to retrain and evaluate future runs? 14 |

## **2. Conceptual Glossary of AI Product Architecture**

Understanding AI product architecture requires a standardized, high-dimensional vocabulary that bridges the gap between machine learning capabilities, interface design, and SaaS financial economics.

| Term | Doctrinal Definition | Systemic Implication |
| :---- | :---- | :---- |
| **AI Product Architecture** | The systemic discipline of selecting, shaping, rejecting, and designing AI capabilities based on workflow fit, user tolerance, data readiness, evaluation clarity, risk level, cost-to-serve, and measurable business value. | Acts as the architectural gateway and control gate before any technical implementation, code construction, or model selection begins. |
| **AI-Shaped Hole Fallacy** | The erroneous assumption that because AI can be integrated into a workflow, the workflow has a genuine need for probabilistic reasoning, leading to features that add cognitive overhead, cost, and verification debt without resolving structural bottlenecks.5 | Causes high-investment product failures by substituting conversational interfaces or generative models where deterministic logic is superior.4 |
| **Automation** | An operational strategy where an AI system executes a complete task or sequence of tasks within a workflow without requiring real-time human intervention or validation prior to execution.9 | Appropriate only where inputs are bounded, outcomes are highly verifiable, and the cost of occasional execution failure is low.9 |
| **Augmentation** | An operational strategy where the AI system assists a human operator by drafting, summarizing, reviewing, or suggesting content, while the human retains full agency, execution authority, and legal accountability.9 | Preserves the human's interpretive space and cognitive engagement, making it highly suitable for nuanced, contextual, and high-consequence tasks.9 |
| **Delegation** | The structured transfer of bounded subtasks from a human to an AI system under strict execution constraints, where the system performs the work but must present its outputs for human validation.16 | Minimizes human cognitive fatigue while maintaining clear accountability, acting as a middle-tier posture between automation and augmentation.17 |
| **Decision Support** | An interaction paradigm where the AI system structures evidence, maps trade-offs, highlights risks, and ranks options, leaving the final selection and execution of authority entirely to the human operator.13 | Mitigates automation bias by preventing the system from proposing a single "correct" answer, forcing active human cognitive processing.13 |
| **Workflow Fit** | The measure of how cleanly an AI capability integrates into the existing sequence of actions, data models, and user interfaces of an enterprise process, without introducing disruptive friction or validation bottlenecks.4 | Determines user adoption; high model accuracy cannot overcome a poor workflow fit that demands frequent context-switching or manual copy-pasting.4 |
| **User Tolerance** | The maximum threshold of latency, uncertainty, error rates, and manual review overhead that a specific user class is willing to accept in exchange for the utility provided by an AI system.19 | Governs the choice of product surface; low-tolerance environments require invisible backend AI or autocomplete, while high-tolerance environments permit chat. |
| **Data Readiness** | The state of structural, legal, and operational fitness of an organization's data assets, determined by whether the required information is accessible, governed, permissioned, clean, and representative of the target use case.21 | Evaluated on a use-case-specific basis; general-purpose data preparation is insufficient to support targeted model reasoning.22 |
| **Evaluation Clarity** | The ability to establish objective, measurable success criteria, baseline performance thresholds, and systematic evaluation rubrics for a probabilistic system prior to writing production code.2 | Ensures the system is testable; if success cannot be programmatically or systematically evaluated, the product cannot be safely scaled.2 |
| **Cost-to-Serve** | The comprehensive financial and infrastructure cost required to deliver a single completed AI task or transaction, spanning token consumption, retrieval overhead, hosting, API calls, logging, and human verification costs.8 | Directly impacts gross margins; high-token reasoning models must be reserved for high-value transactions to prevent margin erosion.8 |
| **Value Design** | The strategic framework that aligns AI capabilities with concrete business outcomes, such as cycle-time reduction, accuracy improvements, and margin protection, rather than relying on qualitative engagement metrics.3 | Rejects the labor-replacement fantasy, focusing instead on throughput enhancement, error mitigation, and specialized knowledge democratization.23 |
| **No-AI Decision** | The deliberate architectural determination that a deterministic software mechanism, workflow redesign, or interface improvement is more reliable, cost-effective, and safe than deploying a probabilistic model.4 | Handled as a positive, successful product outcome that conserves engineering capital and avoids technical debt.4 |
| **Product Surface** | The specific user interface or API gateway through which the AI's capabilities are exposed to and controlled by the user, ranging from open-ended chat inputs to contextual inline suggestions and invisible backend ranking models.14 | Shapes user trust and interaction style; selected dynamically based on risk, latency requirements, and user tolerance metrics.14 |

## **3. The Use-Case Selection Framework**

Selecting viable AI use cases is not a search for technical feasibility alone. The fact that a frontier model can perform a task in a demo does not mean the workflow is ready for probabilistic automation, the data is usable, the users will tolerate the interaction, or the economics survive production scale.

The Use-Case Selection Framework operates as a product architecture gate. It evaluates whether the proposed capability belongs in one of five paths:

1. **No-AI / Deterministic Path** — solve with rules, workflow redesign, database structure, search, forms, templates, or conventional software.
2. **Discovery Experiment** — validate the problem, workflow, user tolerance, and value before model work begins.
3. **Prototype / Pilot** — run a bounded AI experiment with limited blast radius.
4. **Production Design** — proceed to architecture, evals, governance, telemetry, and implementation.
5. **Reject / Defer** — stop because a fatal flaw exists or the value case is weak.

```text
USE-CASE SELECTION FLOW

[ Candidate Use Case ]
        |
        v
[ 1. Is there a real workflow pain? ]
        |
        +-- no --> [ Reject / Defer ]
        |
        v
[ 2. Is AI the right mechanism? ]
        |
        +-- no --> [ No-AI / Deterministic Path ]
        |
        v
[ 3. Is required data available, permissioned, and representative? ]
        |
        +-- no --> [ Data Readiness Work / Defer ]
        |
        v
[ 4. Can success be evaluated before production? ]
        |
        +-- no --> [ Discovery Experiment / Eval Design ]
        |
        v
[ 5. Are risks reversible, governable, and acceptable? ]
        |
        +-- no --> [ Reject / Redesign / Human-Only Gate ]
        |
        v
[ 6. Will users tolerate latency, uncertainty, and review burden? ]
        |
        +-- no --> [ Redesign Product Surface ]
        |
        v
[ 7. Can the system integrate without workflow distortion? ]
        |
        +-- no --> [ Workflow Redesign / API Work First ]
        |
        v
[ 8. Do unit economics survive production volume? ]
        |
        +-- no --> [ Route Optimization / No-AI / Reject ]
        |
        v
[ 9. Can operations monitor, contain, and improve it? ]
        |
        +-- no --> [ Operational Readiness Work ]
        |
        v
[ 10. Is adoption plausible and valuable? ]
        |
        +-- no --> [ Discovery Experiment / Defer ]
        |
        v
[ Production Design Candidate ]
```

### **Use-Case Gate Dimensions**

| Dimension | Core Question | Passing Evidence |
| :---- | :---- | :---- |
| **Workflow Pain** | Is there a real bottleneck, delay, error pattern, or unmet user need? | Baseline cycle time, error rate, support burden, user interviews, workflow observation. |
| **AI Suitability** | Does the task require semantic interpretation, synthesis, classification, or language flexibility? | Clear reason deterministic alternatives are insufficient. |
| **Data Readiness** | Is the required data accessible, permissioned, representative, and governed? | Source inventory, data lineage, access model, sample corpus, privacy review. |
| **Evaluation Clarity** | Can success and failure be measured? | Golden set, rubric, task-specific metrics, human review procedure. |
| **Risk and Reversibility** | What happens when the model is wrong? | Risk tier, reversibility plan, human gate, rollback/compensation policy. |
| **User Tolerance** | Will users accept latency, uncertainty, corrections, and review burden? | Persona-specific tolerance model, usability test, correction-rate target. |
| **Integration Fit** | Does the feature slot into the workflow without copy-paste theater? | API availability, UI surface plan, state ownership, transaction boundaries. |
| **Cost-to-Serve** | Can the feature be delivered profitably at expected usage? | Route cost estimate, token/retrieval/tool/review costs, margin model. |
| **Operational Readiness** | Can the system be monitored, rolled back, and improved? | Telemetry, evals, runbook, owner, incident and feedback loop. |
| **Adoption and Value** | Will users actually change behavior, and will the business capture value? | Adoption hypothesis, value metric, incentive analysis, change plan. |

Scoring is a structured decision aid, not a mathematical oracle. A high score does not override a fatal flaw. A low score does not always kill an idea; it may route the opportunity to workflow redesign, data readiness, or discovery experimentation.

## **4. The Automation versus Augmentation Matrix**

AI product architecture must decide how much authority the system receives. The key design question is not whether the model is “smart enough,” but where human judgment, machine execution, verification, and accountability belong in the workflow.

Automation and augmentation are not opposites. A system can automate information retrieval while preserving human decision authority. It can automate drafting while requiring human approval. It can automate execution only where inputs are bounded, errors are reversible, and verification is reliable.

### **Human-AI Allocation Principles**

| Principle | Meaning |
| :---- | :---- |
| **Automate bounded work, not accountability.** | The system may perform tasks, but responsibility must remain assigned to a human role or organizational control. |
| **Separate recommendation from execution.** | Advice, draft, approval, and action should be distinct workflow states. |
| **Use humans where interpretation matters.** | High-context, high-liability, ambiguous, or value-laden decisions require human authority. |
| **Use machines where verification is cheap.** | Automation fits best where outputs can be checked by schema, tests, source-of-record APIs, or deterministic constraints. |
| **Preserve human situational awareness.** | Highly automated systems need handoff, explanation, rehearsal, and fallback controls. |
| **Design against overtrust and undertrust.** | Interfaces should calibrate confidence, show evidence, capture corrections, and avoid fluent-but-false authority. |

### **Automation vs. Augmentation Matrix**

| Product Posture | System Authority | Best-Fit Task Type | Validation Cost | Failure Consequence | Product Surface | Required Controls |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **No-AI / Deterministic** | No model authority. | Exact math, strict business rules, relational lookup, compliance checks with finite logic. | Low via deterministic tests, or impossibly high for probabilistic output. | Medium to extreme. | Forms, tables, filters, APIs, rules engines. | Schema validation, database constraints, deterministic tests, audit logs. |
| **Decision Support** | System structures evidence and options; human decides. | Legal, medical, financial, compliance, strategy, incident review. | High. | High. | Evidence cockpit, option matrix, risk panel. | Human final decision, source links, independent judgment step, reason logging. |
| **Augmentation** | System drafts or suggests; human edits and approves. | Writing, summarization, customer replies, internal analysis, document review. | Medium. | Low to high depending on domain. | Side-by-side editor, suggested reply card, review panel. | Accept/reject/edit capture, citation/evidence display, user-owned final action. |
| **Delegation** | System performs bounded subtask; human reviews output or exceptions. | Extraction, routing, classification, test generation, structured document processing. | Low to medium. | Low to medium if reversible. | Queue, checklist, structured output panel. | Confidence thresholds, schema validation, exception queue, rollback/retry limits. |
| **Automation** | System acts without real-time human approval. | High-volume, low-risk, reversible, easily verified workflows. | Low. | Low. | Invisible backend route, automated queue, rules-bound agent. | Hard policy gates, source-of-record verification, monitoring, circuit breakers. |
| **Blocked / Human-Only** | System may assist with evidence but cannot decide or execute. | Irreversible, safety-critical, legally sensitive, or existential-risk workflows. | High or uncertain. | Extreme. | Manual workflow with optional evidence support. | Multi-human approval, deterministic controls, complete audit trail, model action disabled. |

### **Design Controls by Cognitive Stage**

| Cognitive Stage | Safe AI Role | Unsafe Anti-Pattern |
| :---- | :---- | :---- |
| **Information Acquisition** | Retrieve, classify, summarize, cluster, and surface relevant material. | Hide missing evidence or retrieve from unauthorized sources. |
| **Information Analysis** | Compare evidence, extract patterns, detect anomalies, draft explanations. | Present unsupported synthesis as fact. |
| **Decision Selection** | Rank options, show tradeoffs, identify risk, ask clarifying questions. | Pick a single “correct” decision in high-impact contexts. |
| **Action Implementation** | Execute bounded, reversible, verified actions. | Mutate external systems without authorization, idempotency, or verification. |

The correct posture is selected by risk, reversibility, validation cost, user tolerance, and workflow value—not by model capability alone.

## **5. Workflow Fit Mapping and Task Decomposition**

AI systems fail when they are treated as magic overlays on top of un-optimized, unchanged operational processes.4 True product value is unlocked when the workflow itself is systematically decomposed, decisions are isolated, and touchpoints are re-engineered around the capabilities and limitations of probabilistic models.4

### **Task Decomposition Mechanics**

Product architects must operate on the fundamental truth that **the model is not the unit of work**.4 Workflows must be decomposed into granular, discrete tasks (e.g., intake, triage, retrieval, synthesis, verification, write-back).4 This allows the architect to isolate the exact bottlenecks where cognitive variability, semantic ambiguity, or unstructured data processing create systemic delays.4 Instead of attempting to automate an entire role, the system targets only the highly specific sub-problems that decompose into independent, evaluable tasks.17

### **Workflow Fit Map**

The operational map below illustrates how AI should be inserted into a high-volume, unstructured document intake and compliance workflow. The model is not the workflow. The workflow is decomposed into stages, and each stage receives the lowest-risk mechanism that can satisfy its task.

```text
WORKFLOW FIT MAP: DOCUMENT INTAKE AND COMPLIANCE REVIEW

[ Emails / customer feedback / PDF contracts / scanned attachments ]
        |
        v
+--------------------------------------------------------------+
| STAGE 1: INTAKE AND NORMALIZATION                            
| Mechanism: parser + OCR + lightweight extraction route        
| Input: messy documents and message text                       
| Output: validated structured JSON + source references         
| AI role: extract and normalize where deterministic parsing ends
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| STAGE 2: EVIDENCE RETRIEVAL                                  
| Mechanism: hybrid retrieval + permission filter + reranker   
| Input: structured payload, account metadata, policy corpus    
| Output: relevant source passages with citations               
| AI role: retrieve and rank candidate evidence                 
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| STAGE 3: POLICY ANALYSIS AND DRAFT SYNTHESIS                  
| Mechanism: governed synthesis route                           
| Input: validated JSON + retrieved evidence + policy rules     
| Output: draft memo, risk flags, missing evidence list         
| AI role: synthesize, compare, explain                         
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| STAGE 4: HUMAN VERIFICATION GATE                              
| Mechanism: evidence cockpit + diff review + approval capture  
| Input: draft memo, citations, extracted fields, risk flags    
| Output: approved, edited, rejected, or escalated package      
| AI role: assist review; never silently approve                
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
| STAGE 5: DETERMINISTIC WRITE-BACK                             
| Mechanism: API / ERP / CRM transaction with schema validation 
| Input: signed and verified payload                            
| Output: committed transaction or explicit failure             
| AI role: none at transaction boundary                         
+--------------------------------------------------------------+
```

### **Workflow-Fit Rules**

| Workflow Stage | AI Belongs When | AI Does Not Belong When |
| :---- | :---- | :---- |
| **Intake** | Inputs are messy, varied, unstructured, or multilingual. | Inputs already arrive in clean structured fields. |
| **Retrieval** | Evidence is spread across unstructured documents or semantic sources. | The answer is a direct database field or exact lookup. |
| **Synthesis** | Human review benefits from summarized evidence, options, or risk flags. | Output requires exact arithmetic, legal execution, or direct authority. |
| **Verification** | AI can highlight inconsistencies, missing evidence, or likely errors. | The system hides uncertainty or makes approval feel automatic. |
| **Write-back** | AI has no direct authority; it may prepare a payload for review. | The model mutates systems without deterministic validation and authorization. |

Use route classes rather than vendor names in architecture diagrams. Model catalogs change. Workflow responsibilities do not.

### **High-Yield versus Low-Yield AI Insertion Points**

When mapping workflows, architects must systematically identify where AI belongs and where it must be aggressively kept out:

| High-Yield AI Insertion Points | Systemic Value Generated | Low-Yield / Prohibited AI Insertion Points | Structural Hazard / Failed Fit |
| :---- | :---- | :---- | :---- |
| **Messy Language Intake** Converting unstructured, multi-format PDFs, emails, and support tickets into validated JSON schemas.4 | Eliminates manual data-entry delays and reduces transcription errors.4 | **Deterministic Math Calculations** Using an LLM to sum line items, calculate tax rates, or process financial statements. | Models are statistically prone to calculation errors; math must always be routed to deterministic code. |
| **Evidence Synthesis** Condensing multi-source policy documents or technical manuals into summaries grounded by direct citations.9 | Reduces manual lookup times, accelerating research and policy verification phases.9 | **Direct Compliance Decisions** Allowing a model to autonomously approve or deny claims, execute legal transactions, or lock user accounts. | High liability, potential for silent failures, and complete loss of human oversight.9 |
| **Triage & Intent Routing** Classifying ambiguous customer requests and routing them to specialized queues based on semantic intent.4 | Automatically routes tasks to the correct expert queues while filtering out noise.4 | **High-Volume Low-Margin SEO Text** Programmatically generating massive volumes of content to flood search indexes. | Incurs massive API bills while degrading search quality and eroding long-term user trust.8 |
| **Synthesized Review Packages** Highlighting missing data, legal risks, or policy violations in draft documents before execution.4 | Minimizes critical compliance errors and ensures consistent policy adherence across departments.4 | **Direct Database Lookups** Forcing users to query exact record fields (e.g., "what is customer X's phone number") via a conversational chat canvas. | Chat increases latency and cost; a simple relational filter UI is faster, cheaper, and exact.5 |

## **6. AI Use-Case Feasibility Scorecard**

Before approving a candidate AI use case for technical design, product leaders and system architects should evaluate it using a structured feasibility scorecard. The scorecard is not a funding slot machine. It is a shared decision artifact that exposes assumptions, fatal flaws, and required readiness work.

### **Scoring Method**

Each dimension is scored from 1 to 5.

| Score | Meaning |
| :---- | :---- |
| **1** | Poor fit; major unresolved blocker. |
| **2** | Weak fit; significant readiness work required. |
| **3** | Plausible but unproven; discovery or prototype needed. |
| **4** | Strong candidate; bounded pilot likely justified. |
| **5** | Production-design candidate with clear evidence. |

### **Feasibility Scorecard Rubric**

| # | Dimension | Low Readiness: 1–2 | Medium Readiness: 3 | High Readiness: 4–5 |
| :---- | :---- | :---- | :---- | :---- |
| **1** | **Workflow Pain** | Low-frequency, low-value, or already solved by deterministic software. | Clear friction exists but baseline cost/error/time is weakly measured. | High-frequency or high-impact bottleneck with measured baseline. |
| **2** | **AI Suitability** | Requires exact deterministic behavior, math, or finite business rules. | Requires extraction, drafting, classification, or bounded synthesis. | Requires semantic interpretation, ambiguous language, synthesis, or adaptive workflow support. |
| **3** | **Data Readiness** | Data is inaccessible, unpermissioned, unrepresentative, or unowned. | Data exists but requires cleaning, lineage, permissions, or parser work. | Data is accessible, permissioned, representative, versioned, and governed. |
| **4** | **Evaluation Clarity** | Success is subjective or undefined. | Human rubric exists but golden data and automated checks are incomplete. | Task-specific metrics, golden data, review process, and regression gates exist. |
| **5** | **Risk and Reversibility** | Errors are high-impact, irreversible, or legally/safety critical. | Errors are contained but require human remediation. | Errors are reversible, detectable, low-impact, and bounded by controls. |
| **6** | **User Tolerance** | Users demand exactness, instant response, and no review burden. | Users accept limited uncertainty or latency for clear benefit. | Users accept probabilistic assistance, review, async processing, or correction loops. |
| **7** | **Integration Complexity** | Requires brittle UI automation, copy-paste, or legacy systems without APIs. | Standard APIs exist but permissions, transactions, or state boundaries are complex. | Clean APIs, state ownership, auth, and transaction boundaries exist. |
| **8** | **Cost-to-Serve Viability** | Model, retrieval, tool, and review costs threaten margins. | Costs look plausible but depend on routing, caching, or usage controls. | Cost per verified task fits target margin with sensitivity analysis. |
| **9** | **Operational Readiness** | No owner, telemetry, rollback, eval, or incident path. | Basic monitoring exists but behavior and quality tracking are immature. | Traceability, evals, runbooks, feedback loops, and owners exist. |
| **10** | **Adoption Likelihood** | Users resist, workflow change is disruptive, or incentives conflict. | Users are interested but workflow/training burden is material. | Users actively want relief and feature slots into existing surfaces. |
| **11** | **Governance Burden** | Regulated/high-impact use with weak lineage, audit, or policy controls. | Governance path exists but requires additional review or tooling. | Compliance, audit, access control, and review obligations are understood and supportable. |
| **12** | **Strategic Value** | Novelty feature, no moat, easy to copy, weak business connection. | Improves workflow but depends heavily on generic third-party capability. | Builds durable advantage through proprietary workflow, data, distribution, or feedback loop. |

### **Decision Bands**

| Average Score / Condition | Decision |
| :---- | :---- |
| **Any fatal flaw present** | Stop, redesign, or route to deterministic/no-AI path. |
| **Average below 2.5** | Reject or defer. |
| **2.5–3.4** | Discovery experiment or readiness work. |
| **3.5–4.2** | Bounded prototype or pilot. |
| **Above 4.2 with no fatal flaws** | Production architecture design candidate. |

### **Architectural Kill-Switches: Fatal Flaws**

| Fatal Flaw | Hazard | Required Product Response |
| :---- | :---- | :---- |
| **No measured baseline** | Cannot prove improvement or ROI. | Measure current workflow time, cost, error, and user burden before building. |
| **No evaluation path** | Model quality cannot be validated or regressed. | Build a seed golden set and review rubric proportional to risk. |
| **Superior deterministic alternative** | AI adds cost and uncertainty where rules would work. | Route to conventional software design. |
| **Unpermissioned or inaccessible data** | Creates privacy, legal, security, or hallucination risk. | Complete data governance and access work first. |
| **High-impact irreversible action without human gate** | Probabilistic system can cause unrecoverable harm. | Block automation; require human approval and deterministic verification. |
| **Unviable cost-to-serve** | Feature cannot survive production usage. | Redesign route, reduce scope, add caching/batching, or reject. |
| **User review burden exceeds value** | AI shifts work rather than reducing it. | Redesign product surface or reject use case. |
| **No operational owner** | Drift, failures, and incidents become orphaned. | Assign owner, runbook, telemetry, and review cadence before pilot. |

## **7. The User Tolerance Model**

User tolerance defines how much latency, uncertainty, correction work, review burden, and workflow interruption a user will accept in exchange for AI assistance. Product fit depends on the user’s task context, consequence of error, existing workflow habits, and perceived control.

```text
USER TOLERANCE =
  latency tolerance
+ uncertainty tolerance
+ correction tolerance
+ review burden tolerance
+ consequence tolerance
+ workflow interruption tolerance
```

### **Tolerance Dimensions**

| Dimension | Low Tolerance Looks Like | High Tolerance Looks Like | Product Implication |
| :---- | :---- | :---- | :---- |
| **Latency** | User expects instant or near-instant response. | User accepts async processing or long-running analysis. | Choose autocomplete, deterministic route, queue, or async review surface accordingly. |
| **Uncertainty** | User needs exact, stable, repeatable outputs. | User accepts variation, drafts, alternatives, or exploration. | Use deterministic software for exactness; use AI for ambiguous or creative work. |
| **Correction Work** | User will not edit, audit, or repair output. | User expects to review and refine. | Avoid draft-heavy surfaces for low-correction users. |
| **Review Burden** | Verification is expensive or cognitively draining. | Verification is natural and already part of the workflow. | Use evidence displays and structured review only where review is valuable. |
| **Consequence of Error** | Errors create legal, financial, safety, privacy, or trust damage. | Errors are low-impact and reversible. | Increase evidence, approval, and human authority as consequence rises. |
| **Workflow Interruption** | User cannot leave primary task surface. | User can work in a dedicated review cockpit. | Inline UI for low interruption; separate cockpit for high-review workflows. |

### **Product Surface Matrix**

| User / Context | Tolerance Profile | Recommended Product Surface | Required Controls |
| :---- | :---- | :---- | :---- |
| **Writer / Creative Worker** | High variation tolerance; moderate latency tolerance; high edit tolerance. | Editor canvas, draft variants, rewrite controls. | Version history, easy undo, style controls, user-owned final text. |
| **Software Engineer** | Low latency tolerance; low syntax-error tolerance; moderate correction tolerance. | Inline autocomplete, code-aware side panel, test-backed suggestions. | Compile/test hooks, diff view, dependency awareness, no blind execution. |
| **Customer Support Agent** | Low false-fact tolerance; low-to-medium latency tolerance; moderate edit tolerance. | Suggested reply card, ticket summary, source-linked answer. | Human send action, citation to customer record, policy snippets, edit capture. |
| **Corporate Lawyer / Compliance Reviewer** | Zero fake-citation tolerance; high review tolerance; accepts async analysis. | Evidence review cockpit, citation grid, risk checklist. | Source-of-record links, line-level evidence, independent human decision. |
| **Financial Analyst** | Zero calculation tolerance; high audit tolerance; medium latency tolerance. | Exception checklist, deterministic calculation panel, AI explanation layer. | Calculations in code/database, audit trail, human approval for conclusions. |
| **Operations Manager** | Low latency tolerance for triage; low manual review tolerance for benign events. | Background router, queue manager, escalation dashboard. | Confidence thresholds, exception queue, monitoring, rollback route. |
| **Voice User** | Very low conversational latency tolerance; low tolerance for awkward pauses. | Streaming voice interface or hybrid voice/text surface. | Barge-in handling, confirmation for high-impact actions, transcript review. |

### **Voice Latency as a Special Case**

Realtime voice has unusually strict interaction constraints. Users experience long pauses as conversational failure. However, voice speed must not outrun safety, confirmation, or audit needs.

| Voice Architecture | Strength | Risk | Product Rule |
| :---- | :---- | :---- | :---- |
| **Chained STT → LLM → TTS** | Modular, auditable, easier to govern. | Higher latency and turn-taking friction. | Use where auditability and control matter more than naturalness. |
| **Native speech-to-speech** | Lower latency and more natural interaction. | Harder to inspect intermediate reasoning and policy state. | Use carefully for low-risk or strongly gated workflows. |
| **Co-located modular stack** | Balances latency and auditability. | Higher infrastructure complexity. | Best for enterprise voice where both speed and control matter. |

The product surface should be selected by user tolerance and consequence, not by fascination with the most conversational interface.

## **8. The Evaluation Clarity Checklist**

A probabilistic feature is not product-ready until the team can define what success means, how failure will be detected, and what happens when confidence drops. “It feels smarter” is not an evaluation architecture. It is a horoscope with a GPU bill.

### **Evaluation Readiness Checklist**

| # | Readiness Item | Required Artifact | Risk-Tier Notes |
| :---- | :---- | :---- | :---- |
| **1** | **Expected output defined** | Schema, rubric, acceptance criteria, or source-of-record predicate. | High-risk workflows require explicit invalid-output handling. |
| **2** | **Human baseline measured** | Current task time, error rate, rework rate, cost, and user pain. | Without baseline, ROI and quality claims are guesswork. |
| **3** | **Representative test set assembled** | Seed golden set or evaluation corpus proportional to risk. | Low-risk may start small; regulated/high-impact needs stronger expert validation. |
| **4** | **Metrics selected by task type** | Extraction, retrieval, generation, tool-use, review, and business metrics. | LLM-as-judge may assist but should not be the only validator for high-risk tasks. |
| **5** | **Failure taxonomy defined** | Hallucination, omission, citation failure, wrong action, unsafe output, privacy leak, bad routing, etc. | Failure classes should map to severity and remediation. |
| **6** | **Escalation behavior specified** | Block, retry, ask clarification, route to human, degrade, or fail closed. | High-impact workflows require explicit human or deterministic gates. |
| **7** | **Feedback capture designed** | Accept, reject, edit, override reason, source correction, user confidence. | Capture sensitive content through secure references and retention policy. |
| **8** | **Release threshold defined** | Minimum quality, maximum failure rate, cost-to-serve ceiling, latency target. | Thresholds should be risk-tiered, not universal. |
| **9** | **Production monitoring planned** | Live drift metrics, user correction trends, cost, latency, incident triggers. | Monitoring must connect to owner and runbook. |
| **10** | **Business outcome mapped** | KPI tied to cycle time, throughput, error reduction, revenue, retention, or risk reduction. | Vanity engagement metrics are insufficient. |

### **Metric Families by Task Type**

| Task Type | Useful Metrics | Weak or Insufficient Metrics Alone |
| :---- | :---- | :---- |
| **Extraction** | Exact match, field-level precision/recall, schema validity, missing-field rate. | Overall thumbs-up score. |
| **Classification / Routing** | Precision, recall, confusion matrix, escalation rate, false-negative cost. | Accuracy alone when classes are imbalanced. |
| **Retrieval / RAG** | Context recall, citation validity, answer support, source permission correctness. | Similarity score alone. |
| **Summarization / Drafting** | Claim support, omission rate, edit distance to accepted version, human acceptance reason. | BLEU/ROUGE alone. |
| **Tool Use / Agentic Action** | Task completion, source-of-record verification, idempotency, action error rate. | Model-reported success. |
| **Decision Support** | Evidence completeness, risk identification, calibration, human decision quality. | Persuasiveness or fluency. |
| **Business Outcome** | Cycle-time reduction, rework reduction, throughput, margin, support deflection, risk reduction. | Session count or novelty engagement. |

### **Evaluation Gate Outcomes**

| Evaluation Result | Product Decision |
| :---- | :---- |
| **Clear improvement with acceptable risk and cost** | Proceed to pilot or production design. |
| **Quality acceptable but cost too high** | Redesign routing, caching, model size, or task scope. |
| **Quality promising but eval weak** | Continue evaluation design before pilot. |
| **Output useful but verification burden too high** | Redesign product surface or reject. |
| **High-risk failure modes unresolved** | Block production; add human gate or deterministic alternative. |
| **No measurable baseline improvement** | Reject or return to workflow discovery. |

Evaluation clarity is a prerequisite to product architecture. If the team cannot say what good means, it is not ready to build.

## **9. The Data Readiness Model**

AI product readiness is use-case-specific. An organization can have excellent analytics data and still be unready for a specific AI workflow if the needed sources are inaccessible, stale, unpermissioned, unrepresentative, or impossible to evaluate.

Data readiness must be assessed before model selection. Poor data readiness does not merely reduce accuracy; it creates hallucination, leakage, evaluation failure, user distrust, and product abandonment.

### **Core Dimensions of Data Readiness**

| Dimension | Product Question | Required Evidence |
| :---- | :---- | :---- |
| **Availability** | Can the system access the required data at the moment of use? | API availability, latency, uptime, retrieval path, fallback behavior. |
| **Permission and Governance** | Is the system allowed to use this data for this user, tenant, purpose, and model route? | ACL/RLS policy, data classification, consent/contract basis, tenant boundary. |
| **Quality and Completeness** | Is the data accurate, deduplicated, complete, and fit for the task? | Data quality report, missingness analysis, duplicate detection, field validation. |
| **Structure and Parseability** | Can the system reliably transform the data into usable context or features? | Schema, parser output, OCR/layout confidence, metadata, chunking policy. |
| **Lineage and Provenance** | Can the system prove where the data came from and how it changed? | Source IDs, version history, transformation lineage, lifecycle state. |
| **Freshness and Conflict State** | Is the data current, and what happens when sources disagree? | Freshness metadata, source-of-record hierarchy, conflict policy. |
| **Representativeness** | Does the data match the real production population and edge cases? | Sampling analysis, historical cases, bias/coverage review. |
| **Evaluation Data** | Does the team have examples with trusted target outputs? | Golden set, review rubric, expert-labeled cases, failure examples. |
| **Retention and Deletion** | Can data be retained, archived, or deleted according to policy? | Retention schedule, deletion workflow, secure evidence references. |
| **Operational Ownership** | Who owns fixes when data breaks? | Data owner, SLA, escalation path, incident workflow. |

### **Data Readiness Maturity Model**

| Level | Readiness State | Characteristics | Allowed Product Use | Required Next Step |
| :---- | :---- | :---- | :---- | :---- |
| **Level 0** | **Unknown** | Data sources, owners, permissions, and quality are undocumented. | No AI use. | Inventory sources and owners. |
| **Level 1** | **Accessible but Ungoverned** | Data can be reached, but permissions, lineage, quality, or retention are unclear. | Offline exploration only with safe data. | Establish governance and classification. |
| **Level 2** | **Prototype Ready** | Data sample exists; basic permissions and quality issues are known. | Local prototype or evaluation sandbox. | Build parser, lineage, and seed eval set. |
| **Level 3** | **Pilot Ready** | Permissions, source lineage, parser behavior, and eval set exist for bounded scope. | Limited pilot with human review. | Add monitoring, freshness, and incident handling. |
| **Level 4** | **Production Ready** | Data is governed, permissioned, versioned, monitored, and evaluable. | Production AI workflow within approved risk tier. | Continuous quality, drift, freshness, and access monitoring. |
| **Level 5** | **Adaptive / Governed at Scale** | Data lifecycle, evals, access controls, telemetry, and feedback loops are automated. | Scaled production and agentic workflows where otherwise appropriate. | Periodic governance and product-value review. |

### **Data Readiness Kill-Switches**

| Kill-Switch | Product Decision |
| :---- | :---- |
| Required data is unpermissioned or legally unclear. | Stop. Complete governance review before model work. |
| Required data is inaccessible at runtime. | Redesign workflow, API, or data pipeline. |
| Source authority is unclear or conflicting. | Define source-of-record hierarchy before launch. |
| Tenant isolation cannot be enforced. | Block production use. |
| No evaluation examples exist. | Build seed evaluation set before pilot. |
| Data is stale and freshness cannot be detected. | Restrict to low-risk or non-current workflows until fixed. |

## **10. The Risk-to-Product Surface Map**

Risk must shape the product surface. The same model behavior may be acceptable as a private draft, dangerous as a recommended decision, and unacceptable as an autonomous action. Product architecture should map risk tier to autonomy, interface, evidence, review, and execution authority.

| Risk Tier | Failure Consequence | Maximum AI Authority | Recommended Product Surface | Evidence Requirement | Execution Control |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Negligible** | Cosmetic, stylistic, or reversible formatting issue. | Suggest or apply reversible changes. | Inline suggestion, editor assist, low-friction autocomplete. | Basic trace and undo history. | User can undo or override immediately. |
| **Low** | Minor inconvenience, benign misrouting, easily corrected internal error. | Delegate bounded task or suggest action. | Suggested draft card, queue route, structured form assist. | Confidence, reason, source field, or simple trace where useful. | Human can reject, edit, undo, or reroute. |
| **Medium** | Meaningful business error, customer-facing mistake, or workflow delay. | Draft, classify, summarize, or recommend; human approves. | Side-by-side review, checklist, evidence-linked summary. | Source links, diff view, validation result, uncertainty display. | Explicit human approval before external send/write. |
| **High** | Legal, financial, privacy, safety, or compliance exposure. | Decision support only; no autonomous execution. | Evidence cockpit, risk register, exception checklist. | Line-level grounding, source-of-record verification, audit trail. | Human decision required; override reason captured. |
| **Extreme** | Physical harm, insolvency, irreversible transaction, regulated enforcement action, or systemwide security risk. | AI may organize evidence only; action authority blocked. | Manual control surface with optional evidence support. | Complete evidence package, deterministic checks, multi-party review. | Multi-human authorization or manual-only execution. |

### **Surface Design Rules**

| Rule | Meaning |
| :---- | :---- |
| **Higher risk requires less autonomy.** | Do not compensate for high consequence with prettier explanations. |
| **Evidence must become more concrete as risk rises.** | Move from confidence hints to source links to source-of-record verification. |
| **Execution is a separate permission.** | A model that can draft a decision is not automatically allowed to execute it. |
| **Undo is not enough for high impact.** | Some actions require pre-approval, not post-hoc correction. |
| **The UI must communicate system role.** | Users should know whether AI is suggesting, drafting, reviewing, deciding, or acting. |
| **Trust repair must be designed.** | Corrections, appeals, overrides, and audit trails are product features, not support leftovers. |

## **11. The ROI and Value Design Model**

AI value is not created by generating outputs. It is created when the product improves a measurable workflow outcome after accounting for serving cost, verification cost, failure cost, adoption cost, and value capture. Time saved is not automatically money saved. A feature can reduce drafting time while increasing review burden, liability, support load, or infrastructure cost.

### **Risk-Adjusted Value Formula**

```text
V_net =
  V_captured
- C_serve
- C_verify
- C_failure_expected
- C_adoption
- C_operational_change
```

Where:

| Variable | Meaning | Examples |
| :---- | :---- | :---- |
| **V_captured** | Value the organization actually captures from the improved workflow. | Paid usage, reduced support tickets, faster cycle time converted to capacity, fewer errors, retained customers. |
| **C_serve** | Cost to run the AI system. | Model calls, retrieval, tools, hosting, storage, telemetry, evals. |
| **C_verify** | Cost of human or automated validation. | Review time, approval queues, expert audit, QA sampling. |
| **C_failure_expected** | Expected remediation cost from model failures. | `P_failure × C_remediation`, including support, legal, refunds, rework, reputation, incidents. |
| **C_adoption** | Cost to change behavior. | Training, workflow redesign, documentation, incentives, migration. |
| **C_operational_change** | Cost to operate the new system over time. | Runbooks, monitoring, drift review, vendor management, governance, incident response. |

### **Baseline-Delta Model**

Product teams should calculate value as a delta from the current workflow:

| Baseline Metric | AI System Metric | Value Question |
| :---- | :---- | :---- |
| Current cycle time | AI-assisted cycle time including review | Did total task time actually fall? |
| Current error rate | AI error + human override + missed-error rate | Did quality improve after verification burden? |
| Current cost per task | AI cost per verified task | Did unit economics improve? |
| Current user effort | AI interaction + correction + review effort | Did the product reduce cognitive load? |
| Current throughput | AI-assisted throughput | Did capacity increase without quality collapse? |
| Current risk exposure | AI residual risk exposure | Did the system reduce or increase downside? |

### **Value Capture Modes**

| Value Mode | Valid When | Common Trap |
| :---- | :---- | :---- |
| **Cycle-Time Reduction** | Faster work creates usable capacity or revenue. | Saved minutes do not translate to actual economic value. |
| **Error Reduction** | AI catches mistakes humans miss or standardizes quality. | AI creates new silent errors that are harder to detect. |
| **Throughput Expansion** | Team can handle more cases without proportional staffing. | More throughput creates more downstream review bottlenecks. |
| **Expertise Democratization** | Non-experts safely perform bounded expert-adjacent tasks. | Product hides uncertainty and encourages overconfidence. |
| **Support Deflection** | Users self-serve accurately with fewer tickets. | Bad answers generate escalations and trust damage. |
| **Risk Reduction** | System improves compliance, auditability, or detection. | Audit trail exists but decision quality does not improve. |
| **Revenue Expansion** | AI unlocks a differentiated paid feature. | Feature is easy to copy or too costly to serve. |

### **ROI Gate**

| Condition | Product Decision |
| :---- | :---- |
| Positive value only under optimistic assumptions. | Run discovery or pilot; do not scale. |
| Value depends on human review being unrealistically fast. | Redesign review surface or reject. |
| Cost-to-serve exceeds margin envelope at expected usage. | Change route, scope, pricing, or reject. |
| AI improves local metric but worsens downstream workflow. | Redesign workflow architecture. |
| Value is measurable, captured, and robust under sensitivity analysis. | Proceed to production design. |

## **12. The Cost-to-Serve Model**

The long-term viability of an AI product is governed by unit economics. Aggregate cloud spend is too blunt. Product architecture needs cost per tenant, request, task, verified task, route, and customer segment.

Static model rate cards should not be embedded as durable doctrine. Provider pricing changes, discounts vary, context tiers differ, cached-token pricing may apply, batch modes may reduce cost, and enterprise agreements can override public rates. Canon should preserve the cost model and rate-card snapshot method, not fossilize one month’s vendor catalog.

### **Cost Allocation Formulas**

```text
Cost_per_tenant =
  (allocated_infrastructure_cost
 + allocated_model_api_cost
 + allocated_storage_cost
 + allocated_observability_cost
 + allocated_support_and_review_cost)
 / active_tenants
```

```text
Cost_per_request =
  request_model_cost
+ retrieval_cost
+ tool_cost
+ storage_and_trace_cost
+ safety_and_eval_cost
+ allocated_infrastructure_cost
```

```text
Cost_per_verified_task =
  total_cost_for_workflow_attempts
  / count(verified_successful_tasks)
```

```text
Cost_waste_ratio =
  cost_of_failed_retried_rejected_or_unverified_work
  / total_ai_workflow_cost
```

### **Cost Components**

| Component | Examples | Product Question |
| :---- | :---- | :---- |
| **Input tokens** | Prompt, context, retrieved chunks, memory, tool descriptions. | Is context bloat driving cost? |
| **Output tokens** | Generated answer, reasoning trace where billed, draft variants. | Is verbosity necessary for value? |
| **Cached tokens** | Prefix cache, semantic cache, provider cache. | Are repeated workloads being deflected safely? |
| **Retrieval** | Embeddings, vector search, reranking, document parsing. | Is evidence retrieval proportionate to task value? |
| **Tool calls** | SaaS APIs, browser actions, database writes, external services. | Are tools bounded and verified? |
| **Review labor** | Human approval, expert validation, QA sampling. | Does verification erase time savings? |
| **Telemetry and evals** | Traces, logs, dashboards, regression runs, shadow evals. | Is operational overhead proportional to risk? |
| **Retries and failures** | Repair loops, rejected outputs, failed tool calls. | Is poor reliability creating hidden COGS? |
| **Infrastructure** | Hosted model pools, GPUs, queues, storage, networking. | Is capacity right-sized and utilized? |

### **Rate-Card Snapshot Template**

Use this table when evaluating a specific product decision. It should be dated and treated as a snapshot.

| Field | Value |
| :---- | :---- |
| **Date checked** |  |
| **Pricing source** |  |
| **Provider** |  |
| **Model / route name** |  |
| **Input price per 1M tokens** |  |
| **Cached input price per 1M tokens** |  |
| **Output price per 1M tokens** |  |
| **Batch discount** |  |
| **Priority / latency premium** |  |
| **Data residency or compliance premium** |  |
| **Context window tier** |  |
| **Tool or hosted feature charges** |  |
| **Enterprise discount assumption** |  |
| **Notes / caveats** |  |

### **Cost-to-Serve Gate**

| Cost Finding | Product Decision |
| :---- | :---- |
| Cost per verified task is below margin target and stable under expected usage. | Proceed. |
| Cost is acceptable only with caching or routing assumptions. | Pilot with explicit telemetry and kill switch. |
| Cost explodes under retries, long context, or agent loops. | Redesign architecture before launch. |
| Cost exceeds willingness-to-pay or margin envelope. | Change pricing, scope, route, or reject. |
| Cost cannot be measured at task level. | Build cost telemetry before scaling. |

Cost-to-serve must be evaluated at the workflow level. A cheap model call can still produce an expensive product if it causes retries, review burden, bad routing, or user abandonment.

## **13. AI Product Pattern Taxonomy**

AI product patterns combine product surface, autonomy level, evaluation method, risk controls, and cost profile. A pattern is not just a UI shape. It defines what the system is allowed to do and how users verify, correct, trust, or reject its behavior.

| Pattern | Best-Fit Workflows | Product Surface | Authority Level | Evaluation Method | Required Controls | Common Anti-Pattern |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Assistant** | Brainstorming, exploratory search, research support, low-risk drafting. | Chat or conversational workspace. | Suggests and explains. | Task success, answer support, user outcome, correction patterns. | Source display where factual, memory boundaries, clear limitations. | Using chat for structured tasks better served by forms or filters. |
| **Copilot** | Code, writing, form completion, active task support. | Inline suggestions, ghost text, side panel. | Suggests; user accepts. | Acceptance rate, edit distance, compile/test result, task completion. | Easy reject/undo, context boundary, validation hooks. | Encouraging blind acceptance in high-risk work. |
| **Autofill / Extraction** | Invoices, forms, CRM fields, receipts, structured document intake. | Field-level suggestions or extracted JSON. | Drafts structured fields. | Exact match, field-level F1, schema validity, missing-field rate. | Human review for material fields, schema validation, source highlights. | Direct database write without review or confidence gating. |
| **Reviewer / Checker** | Contract review, compliance gap detection, security triage, QA. | Risk panel, checklist, highlighted evidence. | Flags issues; does not execute. | Precision/recall, false-negative rate, expert review. | Evidence links, severity labels, reviewer override capture. | Letting checker mutate the source artifact. |
| **Retriever / Synthesizer** | Knowledge search, policy navigation, research synthesis. | Answer with citations, evidence packet, source panel. | Synthesizes from evidence. | Context relevance, citation validity, answer support, freshness. | Permission filters, citation verification, conflict disclosure. | Ingesting unmanaged corpora and trusting generated citations. |
| **Triage / Router** | Support tickets, alerts, intake queues, lead routing. | Invisible or queue-facing classifier. | Routes or prioritizes bounded items. | Confusion matrix, escalation rate, false-negative cost. | Confidence threshold, manual queue, monitoring by class. | Using expensive reasoning models where metadata/rules suffice. |
| **Advisor** | Planning, diagnosis support, risk analysis, expert decision support. | Evidence cockpit, option matrix, scenario panel. | Recommends and structures tradeoffs. | Expert rubric, decision quality, evidence completeness, calibration. | Human final decision, source-of-record links, uncertainty disclosure. | Allowing advisor to execute financial, legal, or medical actions. |
| **Agent** | Bounded cross-application workflows, scheduling, information gathering, low-risk automation. | Task console, plan trace, approval checkpoints. | Executes bounded steps under policy. | Task completion, tool success, verification, intervention rate. | Tool contracts, idempotency, action verification, loop and budget caps. | Unmonitored agent with broad read/write access. |
| **Background Automation** | Spam filtering, benign ranking, deduplication, low-risk routing. | Mostly invisible with settings/appeal surface. | Acts automatically inside bounded scope. | A/B tests, precision/recall, complaint rate, drift monitoring. | User override, audit trace, fallback rules, monitoring. | Hidden manipulation with no user control or appeal. |
| **Evidence-Only AI** | Extreme-risk review, regulated decisions, safety-critical analysis. | Read-only evidence organization surface. | Organizes evidence only; cannot decide or execute. | Evidence completeness, source validity, reviewer usefulness. | Manual authority, deterministic controls, multi-party approval where required. | Treating generated synthesis as authorization. |

Product patterns should be selected after use-case scoring, risk mapping, and user tolerance analysis. The same model can power multiple patterns, but each pattern grants different authority and requires different controls.

## **14. The No-AI Decision Framework**

The defining characteristic of an expert-level AI product architect is the ability to confidently identify when a proposed feature must *not* use artificial intelligence. Rejecting AI in favor of deterministic, robust alternatives is a marker of architectural success, preventing major infrastructure expenses, operational risk, and long-term maintenance burdens.4

### **Deterministic & Relational Triggers**

A proposed product capability must be routed to traditional software engineering development queues (fully bypassing machine learning pipelines) if it matches any of the triggers detailed below:

| Deterministic Trigger Type | Specific Core Criteria | Optimal Software Alternative | Architectural Justification |
| :---- | :---- | :---- | :---- |
| **Exactness Requirements** | Task outputs require absolute mathematical accuracy or adhere to strict compliance rules. | Relational SQL database lookups, transactional rules engines, standard arithmetic calculators.4 | Probabilistic systems operate with statistical variance; they cannot guarantee exact calculations or deterministic logic. |
| **High Validation Costs** | Verifying if a model output is correct is so cognitively demanding that it matches or exceeds the cost of manual work.9 | Standard templates, structured boilerplate builders, and relational database validation fields. | "Verification Debt" erodes the product's entire value proposition, leading to user fatigue and system abandonment.9 |
| **Low Data Readiness** | The required training, fine-tuning, or RAG context data is absent, un-structured, or legally unpermissioned.21 | Clean web form design, structured API metadata capture, and manual data-entry validation flows.22 | AI cannot synthesize data out of thin air; clean structures must exist before deploying cognitive capabilities.22 |
| **Ultra-Low Latency Needs** | Task execution times must remain strictly sub-50ms (e.g., search indexing, standard data table sorting).20 | Standard indexing algorithms, relational search indexing, and client-side JavaScript filters.5 | Large model inference, network routing, and retrieval runs require massive compute budgets that cannot fit within sub-50ms constraints.20 |
| **Friction Out of System** | Process delays are driven by bad organizational incentives, slow human approvals, or outdated software APIs.4 | System process re-engineering, REST API pipeline construction, and user incentive redesigns.4 | Inserting a model on top of a structurally broken process adds complexity without fixing the underlying system constraints.4 |
| **Unviable Gross Margins** | The long-context token, hosting, and retrieval compute costs represent > 30% of the task's transaction value.8 | Traditional, lightweight programming scripts, localized regex parsers, and static templates.8 | Unit economic viability is the backbone of sustainable product growth; unviable features must be built deterministically.8 |

## **15. Product Discovery and Experiment Design Model**

Before scaling production AI, product teams should run discovery experiments that validate workflow pain, user tolerance, data readiness, evaluation clarity, adoption behavior, and cost-to-serve. AI experiments must test the product system, not merely the model demo.

### **Concierge vs. Wizard of Oz**

| Experiment | User Knows What? | Best For | Cannot Prove | Governance Constraint |
| :---- | :---- | :---- | :---- | :---- |
| **Concierge Test** | User knows a human is delivering the service manually. | Validating whether the proposed value actually matters. | Whether users will trust or adopt an automated interface. | Be clear that the service is human-delivered. |
| **Wizard of Oz Test** | User experiences a simulated automated interface while humans perform some backend work. | Validating interface behavior, willingness to use, trust, and workflow fit. | Real model performance, latency, cost, or automation reliability. | Must respect research ethics, privacy, consent, safety, and domain risk. |
| **Hybrid Model-Assisted Pilot** | User or operator knows AI is assisting but bounded by human review. | Learning model limits and correction patterns safely. | Fully autonomous scalability. | Capture edits, failures, and review outcomes with appropriate retention. |
| **Offline Evaluation** | No live user interaction. | Measuring model/task performance on historical cases. | Adoption, workflow fit, or user tolerance. | Use permissioned, representative data. |
| **Internal Controlled Pilot** | Internal users know they are testing a bounded system. | Measuring real workflow impact with limited blast radius. | General market adoption. | Monitor quality, cost, feedback, and incident signals. |

Wizard of Oz experimentation is not a license to deceive users in high-impact contexts. The higher the consequence, the more explicit the disclosure, consent, and review controls must be.

### **Discovery Experiment Taxonomy**

| Experiment Type | What It Proves | Key Metrics | Best Exit Decision |
| :---- | :---- | :---- | :---- |
| **Workflow Observation** | Where bottlenecks, workarounds, and hidden labor exist. | Cycle time, handoff count, rework, interruption, user frustration. | Redesign workflow or select target task. |
| **User Interview** | Whether pain is real and meaningful. | Pain frequency, current workaround, willingness to change. | Continue discovery or reject weak pain. |
| **Concierge MVP** | Whether the proposed service creates value. | Retention, willingness to pay, qualitative delight, task completion. | Define product surface and minimum feature set. |
| **Wizard of Oz MVP** | Whether users behave as expected inside the simulated surface. | Drop-off, trust breakdowns, choices, correction behavior. | Redesign interface or proceed to prototype. |
| **Hybrid Draft-and-Approve Pilot** | Where model output helps, fails, or burdens the user. | Accept rate, edit rate, rejection rate, time saved, failure taxonomy. | Build evals and route policy. |
| **Offline Model Eval** | Whether candidate models/routes meet task thresholds. | Precision, recall, groundedness, schema validity, cost, latency. | Select route or reject model approach. |
| **Internal Pilot** | Whether workflow, operations, and adoption survive real use. | Task delta, quality delta, cost-to-serve, incident rate, user retention. | Proceed, redesign, or stop. |

### **Experiment Design Rules**

| Rule | Meaning |
| :---- | :---- |
| **Test one uncertainty at a time where possible.** | Do not mix model quality, UI design, pricing, and workflow change into one unreadable experiment. |
| **Capture correction data.** | Edits and rejections are product gold; they reveal evaluation cases and workflow mismatch. |
| **Measure total task time.** | Draft speed is irrelevant if review time grows. |
| **Use real-enough data safely.** | Synthetic demos often hide permission, format, edge-case, and messiness problems. |
| **Protect users from high-impact simulation.** | Do not simulate autonomous authority in contexts where users could be harmed or misled. |
| **Define stop conditions.** | Experiments should be able to kill bad ideas cleanly. |

## **16. The Adoption and Change Model**

AI product success is not defined at launch. It is defined when users integrate the system into durable work habits without overtrusting, ignoring, bypassing, or being cognitively dulled by it. Adoption is a behavioral architecture problem.

### **Adoption States and Interventions**

| User State | Observable Signals | Product Risk | Product Intervention | Change Management Response |
| :---- | :---- | :---- | :---- | :---- |
| **Healthy Calibration** | Users accept useful suggestions, reject bad ones, and understand system limits. | Low. | Maintain evidence, correction, and feedback surfaces. | Reinforce best practices and share quality wins. |
| **Overtrust / Complacency** | Users accept outputs with little review; errors propagate downstream. | Silent quality collapse. | Require evidence display, independent judgment step, review prompts, confidence calibration. | Train users on failure modes; reward error catching. |
| **Undertrust / Rejection** | Users ignore feature, revert to manual work, or disable suggestions. | No adoption; wasted investment. | Improve transparency, reliability feedback, undo, and user control. | Involve users in rubric design and pilot iteration. |
| **Motivational Withdrawal** | Users become passive reviewers and stop thinking critically. | Reduced expertise and poor final quality. | Use sequential teaming: human frames problem first, AI assists second. | Redefine roles around expert judgment and final accountability. |
| **Workflow Circumvention** | Users move to unapproved consumer tools or manual side channels. | Shadow AI, data leakage, inconsistent process. | Put useful AI inside the actual workflow with lower friction. | Improve approved tools and procurement path. |
| **Correction Fatigue** | Users spend too much time editing or auditing outputs. | Abandonment or rubber-stamping. | Reduce scope, improve evals, show diffs, route only high-confidence cases. | Reassess value model and staffing assumptions. |
| **Status Threat** | Users fear replacement, deskilling, or surveillance. | Resistance and sabotage. | Make AI role explicit: assistive, bounded, accountable. | Communicate role changes, incentives, and career path. |

### **Adoption Metrics**

| Metric | What It Shows |
| :---- | :---- |
| **Activation Rate** | Whether users try the feature after exposure. |
| **Repeat Use** | Whether the feature becomes habit. |
| **Acceptance / Rejection / Edit Rate** | Whether suggestions are useful and appropriately trusted. |
| **Time-to-Verified-Completion** | Whether total task time improves after review. |
| **Override Reason Distribution** | Why users reject or repair output. |
| **Manual Bypass Rate** | Whether users leave the approved workflow. |
| **Error Catch Rate** | Whether humans remain meaningfully engaged. |
| **Support / Complaint Rate** | Whether the product creates confusion or harm. |
| **Skill Retention Signal** | Whether users can still perform core tasks without AI when needed. |

### **Change Model Requirements**

| Requirement | Purpose |
| :---- | :---- |
| **Role clarity** | Users must know whether AI drafts, reviews, routes, recommends, or acts. |
| **Accountability clarity** | Human and organizational responsibility must be explicit. |
| **Training on failure modes** | Users need examples of plausible AI errors, not just feature demos. |
| **Feedback loops** | Corrections must improve evals, routing, prompts, or product design. |
| **Incentive alignment** | Users should be rewarded for quality and judgment, not blind throughput. |
| **Shadow-AI alternative** | Approved tools must be good enough that users do not flee to unsanctioned ones. |
| **Periodic recalibration** | Adoption patterns should be reviewed as model behavior, workload, and user skill change. |

Adoption is not “users clicked the sparkle button.” Adoption is sustained, safe, value-producing integration into real work.

## **17. Cross-Canon Handoff Map**

AI-ENG-AF opens the Product, Business, and Organizational Architecture volume. It acts as the product gate before implementation: selecting use cases, rejecting bad fits, mapping workflows, defining value, choosing product surfaces, and determining whether AI belongs at all.

AF consumes technical constraints from earlier canon layers and hands product decisions forward into business model, adoption, and enterprise transformation architecture.

### **Upstream Canon Inputs**

| Canon Report | What AF Consumes | Product Architecture Use |
| :---- | :---- | :---- |
| **AI-ENG-B — Context Architecture** | Context windows, memory, state, authority, and prompt/context boundaries. | Determines whether the workflow can fit into safe and usable context structures. |
| **AI-ENG-D — Corpus Engineering** | Data ownership, provenance, lifecycle, metadata, and corpus quality. | Evaluates data readiness and corpus suitability for product use. |
| **AI-ENG-E — Retrieval Pipeline** | Retrieval feasibility, citation support, ranking, and evidence quality. | Determines whether RAG can support the user promise. |
| **AI-ENG-F — Freshness and Conflict Detection** | Source freshness, conflicts, and source-of-record hierarchy. | Determines whether product outputs can stay current and trustworthy. |
| **AI-ENG-J — Throughput Mechanics** | Latency, batching, queueing, token throughput. | Shapes user tolerance, cost-to-serve, and surface choice. |
| **AI-ENG-K — Weight Dynamics** | Model size, quantization, adaptation, capability boundaries. | Informs model suitability and route-class selection. |
| **AI-ENG-L — Serving Architecture** | Routing, provider profiles, fallback, caching, scale. | Informs feasibility, latency, cost, and operational readiness. |
| **AI-ENG-N — Tool Contracts** | Tool schemas, side effects, auth, idempotency. | Determines whether agentic or tool-using product patterns are viable. |
| **AI-ENG-O — Action Verification** | State verification, action ledgers, false-success prevention. | Defines whether automation, delegation, or human approval is required. |
| **AI-ENG-S — Production Pathologies** | Common AI failure modes and brittle-chain behavior. | Feeds fatal-flaw and risk-surface design. |
| **AI-ENG-T — Boundary Defense** | Tenant isolation, prompt injection, egress, policy hierarchy. | Determines product risk tier and required security constraints. |
| **AI-ENG-V — Resource Abuse** | Cost bombs, loop controls, denial-of-wallet. | Feeds cost-to-serve and agent pattern constraints. |
| **AI-ENG-W — UX Resilience** | Degraded modes, continuity, fallback, user state. | Shapes user tolerance and failure UX. |
| **AI-ENG-X — User Trust** | Transparency, calibration, contestability, evidence display. | Shapes product surface, trust repair, and adoption design. |
| **AI-ENG-Y — Human Review** | Review queues, escalation, reviewer quality, approval patterns. | Determines augmentation, delegation, and decision-support boundaries. |
| **AI-ENG-Z — Telemetry** | Traceability, cost, latency, behavior, user correction metrics. | Defines product success measurement and operational readiness. |
| **AI-ENG-AA — Evaluation Architecture** | Golden sets, eval gates, rubrics, regression testing. | Determines evaluation clarity and launch readiness. |
| **AI-ENG-AC — AI Operations** | Incident response, runbooks, rollback, containment. | Determines whether product risks can be operated after launch. |
| **AI-ENG-AD — Governance Architecture** | Policy, audit, procurement, accountability, risk classification. | Defines compliance burden, approval path, and product authority limits. |
| **AI-ENG-AE — Sustainable AI** | Energy, carbon, routing, lifecycle, and cost of compute. | Adds sustainability and resource efficiency to product fit and value design. |

### **Forward Handoff to Volume 11**

| Target Report | AF Concept Handed Forward | Downstream Use |
| :---- | :---- | :---- |
| **AI-ENG-AG — Business Model, Pricing & Packaging Design** | Cost-to-serve, value model, use-case score, route class, margin risk. | Pricing tiers, usage limits, packaging, COGS controls, expansion strategy. |
| **AI-ENG-AH — Organizational Adoption, Training & Change** | User tolerance, adoption hazards, automation posture, workflow disruption. | Training, incentive design, role redesign, change management, skill retention. |
| **AI-ENG-AI — Enterprise Transformation Reference Architecture** | Workflow fit maps, product pattern, integration constraints, no-AI decisions. | Enterprise rollout patterns, system integration, API architecture, governance pathways. |
| **AI-ENG-AJ — Reference Architectures** | Approved product patterns and decision gates. | Reusable implementation blueprints and golden paths. |

### **Core Handoff Rule**

AF must happen before implementation. If the product architecture gate cannot identify workflow pain, AI suitability, data readiness, evaluation clarity, risk posture, user tolerance, cost-to-serve, and measurable value, the correct engineering action is not “try a better model.”

The correct action is to stop, redesign, run discovery, or choose No-AI.

#### **Works cited**

1. Complete Guide to Product Discovery: Methods, Frameworks, - IdeaPlan, accessed June 14, 2026, [https://www.ideaplan.io/guides/the-complete-guide-to-product-discovery](https://www.ideaplan.io/guides/the-complete-guide-to-product-discovery)  
2. What Is AI Product Management? | Galileo, accessed June 14, 2026, [https://galileo.ai/blog/ai-product-management-guide](https://galileo.ai/blog/ai-product-management-guide)  
3. AI Product Management Roadmap & Frameworks: Step-by-Step Guide - Voltage Control, accessed June 14, 2026, [https://voltagecontrol.com/articles/ai-product-management-roadmap-frameworks-step-by-step-guide/](https://voltagecontrol.com/articles/ai-product-management-roadmap-frameworks-step-by-step-guide/)  
4. Workflow Redesign and Human-AI Collaboration - Umbrex, accessed June 14, 2026, [https://umbrex.com/resources/chief-ai-officer-playbook/workflow-redesign-and-human-ai-collaboration/](https://umbrex.com/resources/chief-ai-officer-playbook/workflow-redesign-and-human-ai-collaboration/)  
5. Technology Will Make the Pace of Change Even Faster - Articles - Advisor Perspectives, accessed June 14, 2026, [https://www.advisorperspectives.com/articles/2024/12/30/technology-will-make-the-pace-of-change-even-faster](https://www.advisorperspectives.com/articles/2024/12/30/technology-will-make-the-pace-of-change-even-faster)  
6. Thinks 1499 – Rajesh Jain, accessed June 14, 2026, [https://rajeshjain.com/2025/02/07/thinks-1499/](https://rajeshjain.com/2025/02/07/thinks-1499/)  
7. Austrian economics and AI scaling - Marginal REVOLUTION, accessed June 14, 2026, [https://marginalrevolution.com/marginalrevolution/2024/11/austrian-economics-and-ai-scaling.html](https://marginalrevolution.com/marginalrevolution/2024/11/austrian-economics-and-ai-scaling.html)  
8. Kubernetes FinOps: SaaS Unit Economics | HostingX, accessed June 14, 2026, [https://hostingx.co.il/articles/kubernetes-finops-unit-economics](https://hostingx.co.il/articles/kubernetes-finops-unit-economics)  
9. Structuring Human-AI Productive Interdependence by Strategic Level of Automation Selection for Qualitative Inquiry - arXiv, accessed June 14, 2026, [https://arxiv.org/html/2605.27634v1](https://arxiv.org/html/2605.27634v1)  
10. Structuring Human-AI Productive Interdependence by Strategic Level of Automation Selection for Qualitative Inquiry - arXiv, accessed June 14, 2026, [https://arxiv.org/pdf/2605.27634](https://arxiv.org/pdf/2605.27634)  
11. Cost-to-Serve in AI: The Most Overlooked Metric for Sustainable Margins - Mavvrik: AI, accessed June 14, 2026, [https://www.mavvrik.ai/blog/cost-to-serve-in-ai/](https://www.mavvrik.ai/blog/cost-to-serve-in-ai/)  
12. What Is AI Agent Observability? Why Cost Is The Signal You're Missing - CloudZero, accessed June 14, 2026, [https://www.cloudzero.com/blog/ai-agent-observability/](https://www.cloudzero.com/blog/ai-agent-observability/)  
13. Human–AI Collaboration Across Decision Support, Autonomous ..., accessed June 14, 2026, [https://www.mdpi.com/2071-1050/18/11/5313](https://www.mdpi.com/2071-1050/18/11/5313)  
14. Wizard of Oz | The Real Startup Book - Kromatic, accessed June 14, 2026, [https://kromatic.com/real-startup-book/4-evaluative-product-experiments/wizard-of-oz/](https://kromatic.com/real-startup-book/4-evaluative-product-experiments/wizard-of-oz/)  
15. LLM Training Data Lineage: Provenance, Tracking & Compliance - Atlan, accessed June 14, 2026, [https://atlan.com/know/training-data-lineage-for-llms/](https://atlan.com/know/training-data-lineage-for-llms/)  
16. The Impact of AI Execution Autonomy on User Task Performance and Intervention Behavior in Digital Workflows - RPubs, accessed June 14, 2026, [https://rpubs.com/Ladan/ai-execution-autonomy](https://rpubs.com/Ladan/ai-execution-autonomy)  
17. Toward Human-AI Complementarity Across Diverse Tasks - arXiv, accessed June 14, 2026, [https://arxiv.org/html/2605.04070v1](https://arxiv.org/html/2605.04070v1)  
18. A Model for Types and Levels of Human Interaction with Automation - SlideServe, accessed June 14, 2026, [https://www.slideserve.com/hila/a-model-for-types-and-levels-of-human-interaction-with-automation](https://www.slideserve.com/hila/a-model-for-types-and-levels-of-human-interaction-with-automation)  
19. [論文評述] Edge Intelligence Optimization for Large Language Model, accessed June 14, 2026, [https://www.themoonlight.io/tw/review/edge-intelligence-optimization-for-large-language-model-inference-with-batching-and-quantization](https://www.themoonlight.io/tw/review/edge-intelligence-optimization-for-large-language-model-inference-with-batching-and-quantization)  
20. The enterprise voice AI split: Why architecture — not model quality — defines your compliance posture | VentureBeat, accessed June 14, 2026, [https://venturebeat.com/security/the-enterprise-voice-ai-split-why-architecture-not-model-quality-defines](https://venturebeat.com/security/the-enterprise-voice-ai-split-why-architecture-not-model-quality-defines)  
21. An Introduction to AI-Ready Data - Alexander Thamm [at], accessed June 14, 2026, [https://www.alexanderthamm.com/en/blog/ai-ready-data/](https://www.alexanderthamm.com/en/blog/ai-ready-data/)  
22. Data Readiness Assessment for AI: Checklist, Framework, and Scoring, accessed June 14, 2026, [https://agility-at-scale.com/ai/data/data-readiness-assessment-for-ai/](https://agility-at-scale.com/ai/data/data-readiness-assessment-for-ai/)  
23. Product Frameworks: AI - Productboard, accessed June 14, 2026, [https://www.productboard.com/wp-content/uploads/2024/01/AI-Product-Framework-Guide.pdf](https://www.productboard.com/wp-content/uploads/2024/01/AI-Product-Framework-Guide.pdf)  
24. The AI-shaped hole in personal finance – Z-Connect by Zerodha, accessed June 14, 2026, [https://zerodha.com/z-connect/subtext/the-ai-shaped-hole-in-personal-finance](https://zerodha.com/z-connect/subtext/the-ai-shaped-hole-in-personal-finance)  
25. Human-Centered Artificial Intelligence: Reliable, Safe & Trustworthy - arXiv, accessed June 14, 2026, [https://arxiv.org/pdf/2002.04087](https://arxiv.org/pdf/2002.04087)  
26. Designing Human-Automation Interaction: a new level of Automation Taxonomy - HFES Europe, accessed June 14, 2026, [https://www.hfes-europe.org/wp-content/uploads/2014/06/Save.pdf](https://www.hfes-europe.org/wp-content/uploads/2014/06/Save.pdf)  
27. Chapter: 6 Human-AI Team Interaction - National Academies of Sciences, Engineering, and Medicine, accessed June 14, 2026, [https://www.nationalacademies.org/read/26355/chapter/8](https://www.nationalacademies.org/read/26355/chapter/8)  
28. Preparing Data for AI and Machine Learning: A Production-Ready Playbook - instinctools, accessed June 14, 2026, [https://www.instinctools.com/blog/preparing-data-for-ml-ai/](https://www.instinctools.com/blog/preparing-data-for-ml-ai/)  
29. LLM API Pricing Comparison In 2026: Every Major Model, Ranked By Cost - CloudZero, accessed June 14, 2026, [https://www.cloudzero.com/blog/llm-api-pricing-comparison/](https://www.cloudzero.com/blog/llm-api-pricing-comparison/)  
30. Page 97 – Marketing, Entrepreneurship, India. Updated daily. - Rajesh Jain, accessed June 14, 2026, [https://rajeshjain.com/page/97/?source=user_profile---------0-](https://rajeshjain.com/page/97/?source=user_profile---------0-)  
31. The Top AI Models And Trends Shaping SaaS in 2026 - CloudZero, accessed June 14, 2026, [https://www.cloudzero.com/blog/top-ai-models/](https://www.cloudzero.com/blog/top-ai-models/)  
32. How SaaS Companies Can Profitably Price AI Agents - CloudZero, accessed June 14, 2026, [https://www.cloudzero.com/blog/ai-agent-pricing-models/](https://www.cloudzero.com/blog/ai-agent-pricing-models/)  
33. AI Product Discovery Frameworks Overview - Productboard, accessed June 14, 2026, [https://www.productboard.com/blog/ai-product-discovery-frameworks/](https://www.productboard.com/blog/ai-product-discovery-frameworks/)  
34. Concierge vs. Wizard of Oz Experiments - Learning Loop, accessed June 14, 2026, [https://learningloop.io/blog/concierge-vs-wizard-of-oz](https://learningloop.io/blog/concierge-vs-wizard-of-oz)  
35. Two MVPs every product manager should know, and how to tell them apart, accessed June 14, 2026, [https://www.mindtheproduct.com/wizard-of-oz-vs-concierge-testing-behind-the-curtain-or-behind-the-desk/](https://www.mindtheproduct.com/wizard-of-oz-vs-concierge-testing-behind-the-curtain-or-behind-the-desk/)  
36. Wizard of Oz Experiment: Definition, How It Works, Examples, Tools, Pros and Cons, accessed June 14, 2026, [https://learningloop.io/plays/wizard-of-oz](https://learningloop.io/plays/wizard-of-oz)  
37. Can LLM Agents Simulate Customers to Evaluate Agentic-AI-based Shopping Assistants?, accessed June 14, 2026, [https://arxiv.org/html/2509.21501v1](https://arxiv.org/html/2509.21501v1)  
38. Modeling the Dynamic Agency in Human-AI Collaboration - DRS Digital Library, accessed June 14, 2026, [https://dl.designresearchsociety.org/cgi/viewcontent.cgi?article=1608&context=iasdr](https://dl.designresearchsociety.org/cgi/viewcontent.cgi?article=1608&context=iasdr)

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