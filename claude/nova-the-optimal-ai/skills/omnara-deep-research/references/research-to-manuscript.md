# Turn an investigation into a paper worth reading

Use this route when the commission includes a research paper, technical manuscript, or a substantial evidence-backed article. Choose the form from the contribution: empirical study, methods paper, theory, replication, negative result, or evidence synthesis. An ordinary report need not acquire an experimental costume. Preserve the campaign's existing source and claim IDs; the manuscript is another authored view of that evidence.

## Find the contribution and its spine

Write a working contribution sentence: what question this work resolves or advances, through which mechanism or evidence, for which setting, and with what important limit. Separate what is new in the work from what is merely new to its author. For novelty claims, read the closest relevant prior work and compare the actual mechanism, assumptions, evidence, and scope. A search miss leaves novelty uncertain.

Build the argument before filling sections. For each central claim, locate its supporting observation, derivation, source or analysis, the figure or table that makes it inspectable, and the strongest live objection. Arrange these claims so the reader acquires each prerequisite before needing it. A section earns its place by advancing that argument. Use `assets/manuscript-plan.md` when several sections or revisions need coordination.

Draft the methods and results while the evidence is close. Then write the introduction around the gap the results actually address, position related work around consequential differences, and write the abstract and title last. This is a useful working order, not a mandatory table of contents.

## Compose each part for its intellectual job

The introduction establishes the problem, why existing answers leave a meaningful gap, the approach, and the precise contribution. Give the reader an early map of the argument. Avoid a grand claim about an entire field when the work studies one setting.

The method explains how the conclusion was earned. For experiments, retain data provenance and splits, sampling or selection, baselines, treatment or intervention, implementation and configuration, measurement definitions, exclusions, compute or other resource limits, replication, and analysis choices. Identify decisions made after seeing results. For theory, state assumptions and expose the derivation's decisive steps. For synthesis, explain the actual retrieval, inclusion, interpretation and reconciliation methods. Do not invent missing procedural detail to make the section look complete.

Organize results by the questions or claims they answer. Show the central comparison first, then robustness, ablations or counterexamples when they were actually investigated. Report the denominator, units, relevant uncertainty, variation across repetitions, missing runs and exclusions. Keep exploratory findings separate from prespecified tests. A null or negative result can be the contribution; it does not need a consolation prize made of speculative benefits.

Give each figure or table one principal question. Build it from retained data or supported source values. Explain the population or setup, units, comparison, aggregation, variability and any omitted observations in the caption or nearby text. A reader should be able to understand what a cell, mark, axis or error bar means without reverse-engineering the notebook. Distinguish standard deviation, standard error and intervals; never manufacture them from an unavailable sample. Use a schematic to explain a mechanism and empirical graphics to report measurements, labeling illustrative values. Mention the result the reader should notice in prose instead of repeating every cell.

Discussion interprets the result against the hypothesis and rival explanations, distinguishes demonstrated effects from plausible mechanisms, and explains where the result transfers or fails. Limitations name the actual threats, their consequences and the evidence that could reduce them. The conclusion states the supported contribution and its scope. The abstract compresses problem, approach, decisive result and implication without becoming stronger than the body. Preserve exact numbers and qualifications through every compression.

Keep terminology and symbols consistent. Introduce notation at first use, distinguish the proposed mechanism from its implementation, and let paragraphs carry one inferential move with a clear connection to the next. Trim repeated motivation and adjectives that substitute for evidence. An appendix holds useful detail, not evidence whose absence makes the main claim misleading.

## Review the artifact with fresh eyes

When an independent review is authorized and available, prepare a cold-read packet containing the manuscript, claim/evidence index, methods, full relevant results including negatives and exclusions, and accessible source or run artifacts. Leave the author's expected score, earlier praise and prior reviewer conclusions outside the initial packet. Retain methodological history that affects validity, including post-result hypothesis changes, unsuccessful attempts and selection decisions. Removing evaluative priming must not sanitize the research record.

Ask the reviewer to reconstruct the contribution, test the decisive evidence and identify the most consequential gap before judging the prose. A packet index helps them find primary evidence rather than depending only on the author's chosen summary. Record what was withheld for blinding and which underlying artifacts were accessible. Fresh context establishes reduced conversational priming; it does not prove expert independence, different model lineage or scientific correctness.

Preserve the returned critique in its original form. Map each material concern to a claim, section or artifact; accept it, rebut it with evidence, narrow the claim, or retain it as unresolved. A prose revision cannot repair absent experiments. Compare self-assessment and review through substantive disagreements; calculate a numerical gap only when both ratings actually exist on the same scale. Never invent a missing self-score or treat an average as acceptance authority.

Recheck affected claims and cross-section summaries after revision. Additional research or experiments remain bounded by the commission and budget. When the evidence supports only a draft, deliver a draft with specific gaps. Submission-ready additionally requires the selected venue's current format, references, figures, anonymization where relevant, ethics and disclosure requirements, and accountable author approval. Check current official requirements when submission readiness is requested. Do not infer publication, peer-review acceptance or authorization to submit.

## Lineage

Independently adapted from [AutoResearch](https://github.com/EvoMap/AutoResearch/tree/0fa9a9336fc84a6b069111adb03ca21fabb5394b), especially `ar-runtime/.claude/agents/ar-blind-reviewer.md` and `ar-runtime/.claude/agents/ar-planner.md`. The cold-read packet and complete-result presentation are retained; fixed reviewer counts, venue scores and sanitized methodological history are not. No upstream code or prompt text is bundled.
