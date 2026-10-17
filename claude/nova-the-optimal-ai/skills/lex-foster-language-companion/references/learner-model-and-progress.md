# Keep a learner model they can argue with

An adaptive tutor needs memory, but memory becomes dangerous when it turns a few performances into a verdict about the person. Preserve useful evidence as an editable working model: small, local, and open to correction.

## Track capability, not identity

Record only what changes instruction:

- working language and target language or variety;
- real-world goals and recurring situations;
- accessibility or modality needs;
- correction and challenge preferences;
- language the learner used independently;
- language used after a cue;
- recurring transfer patterns or confusions;
- high-value items due for retrieval;
- evidence that a skill transferred to a changed task.

Do not infer intelligence, motivation, disability, nationality, identity, or “talent” from linguistic performance. A learner may be tired, rushed, anxious, code-switching intentionally, or using a variety the model knows poorly.

## Use four evidence states

- **new:** encountered but not yet produced;
- **supported:** produced with a model, choice, or cue;
- **independent:** met a named production or recognition criterion without immediate support in the trained situation;
- **transferred:** met that same criterion in the same modality without immediate support under a materially changed cue. Recognition transfer remains recognition; it cannot stand for production, listening or speaking.

These states describe observed performance, not permanent mastery. Keep the task, date, modality, and support level near consequential evidence.

“Fragile” is a useful scheduling judgment, not a fifth attainment state. It means the evidence is recent, inconsistent, or highly cue-bound and should be revisited.

## Estimate functional reach plainly

Describe what the learner presently appears able to do:

> In this chat, you handled a polite restaurant request and repaired the word order after one cue. We have not examined spontaneous listening or past-time narration.

If a familiar framework helps orientation, state that the estimate is informal, partial, and not an official rating. Do not convert one writing sample into a global level.

## Let the learner govern correction

Record preferences as current and revisable:

- interruption: immediate, natural pauses, or end-of-turn;
- focus: communication-first, balanced, or fine-grained;
- explanation: compact, contrastive, or deep;
- challenge: supported, stretch, or immersive;
- base-language use: welcome, minimal, or only on request.

Safety, material misunderstanding, and explicit task constraints may still require immediate clarity. Explain the reason rather than treating preference as absolute law.

## Schedule by value and evidence

Choose the next practice item from:

- importance to a real goal;
- likelihood of recurrence;
- communicative or social consequence;
- fragility of evidence;
- opportunity to contrast a transfer pattern;
- time since the last successful retrieval.

Use human-scale timing: later in the session, next session, in a few days, after two intervening missions. Do not imply that an exact forgetting curve has been measured.

## Resume from the first unverified edge

At resumption:

1. confirm the target situation still matters;
2. honor any changed preference immediately;
3. retrieve one high-value item before reteaching it;
4. vary the context enough to test transfer;
5. update the record from observed behavior.

When new evidence contradicts the profile, preserve the newer observation and revise the interpretation. Do not make the learner fight an old JSON file for custody of themselves.

## Keep state optional and portable

Use `assets/learner-profile.template.json` only when continuity is worth the privacy and clerical cost. The learner owns the file, may inspect every field, and may remove sensitive context or delete it entirely.

Without saved state, summarize the live foreground in ordinary conversation and continue. The lost guarantee is cross-session resumption, not the ability to teach.

## Inspect the observation, not the label

For new evidence worth saving, retain the actual prompt and response (a minimal excerpt is enough), the goal ID, modality, specific criterion, observed result and support kind. An audio observation requires audio actually available to the host; do not invent a transcript of unheard speech. `observation` is optional for compatibility with earlier v1 records. Its absence means the state is a historical declaration with no inspectable performance basis, not verified progress. Never invent missing detail to make old records pass.

A transferred observation also identifies an earlier observation and explains what changed. The language, modality and specific criterion stay comparable; simply sharing a broad goal does not establish repair. The validator can reject impossible chronology, broken references, identical cue text and explicit support/result contradictions. It cannot tell whether a paraphrased cue really differs, the language is correct, the criterion tests the diagnosed gap, or a response was honestly observed. Review those facts in the conversation before making a claim.

The blank creation template intentionally needs identity, languages and a real zoned update time before it validates. It contains no evidence. A filled fictional example lives at `examples/progress-and-return/fictional-profile.json`; never copy its observations into a learner’s record. A plain recap can be enough: current goal, actual response and help, unresolved edge, next useful cue. JSON is optional.
