# Signal Loom faculty bearings

This is a conditional library, not an entry point or prompt menu. The Signal Loom skill owns activation, stage, authority, evidence, progressive loading, and completion. Read only the faculty section needed for the live stage. A section supplies conceptual and craft bearings; it never self-activates, widens scope, requires external dependencies, authorizes publication, or overrides the current Loomfile and source boundary.


[Table of Contents]

- [1. Story Spine Builder](#1-story-spine-builder)
- [2. Infographic Forge — Page Constructor](#2-infographic-forge--page-constructor)
- [3. Infographic Theme & Palette Reworker](#3-infographic-theme--palette-reworker)
- [4. Hooksmith & Microcopy Polish](#4-hooksmith--microcopy-polish)
- [5. Viralizer](#infographic-viralizer)
- [6. Toysmith](#infographic-toy-adder)
- [7. Platformizer](#7-platformizer)
- [8. Carouselizer](#8-carouselizer)
- [9. Diagnostic Reviewer](#infographic-diagnostic-reviewer)


## 1. Story Spine Builder
```
Begin by reading the material like it’s already a story — not a pile of facts, but a motion trying to happen.  
Find the pulse. Find the turn. Sense the shape of the idea beneath the surface.  
Your job is to give it bones: a spine of clean, inevitable beats that carry the viewer from curiosity to comprehension with rhythm, tension, and release.

This is **narrative choreography**, not summarization.  
You are aligning information with the way human attention actually moves.

Default behavior: produce the smallest complete story spine that can carry the material. Variants, panelization, and extra beats are optional when they improve the named artifact rather than merely enlarging it.

## 1️⃣ Orientation: The Pulse & The Turn

Skim the content with three questions:

• What is the gravitational center — the idea everything orbits?  
• What sequence of understanding must the viewer travel through to “get it”?  
• Where does the shift occur — the moment the frame changes?  

Output:
• the central theme  
• the core tension  
• the interpretive turn  
• the payoff insight  

Do this in 3–5 sentences. No fluff.

## 2️⃣ Identify the Anchors (Map the Terrain)

Extract the conceptual nodes the story must touch:

• Context anchors — where the world starts  
• Mechanism anchors — how the system or idea actually works  
• Contrast anchors — expectation vs reality  
• Inflection anchors — the spike, break, twist, anomaly  
• Payoff anchors — what it all means  
• Watchpoint anchors — what happens next / what to monitor  

Order them not by appearance in the source, but by **narrative logic** — the way understanding naturally unfolds.

## 3️⃣ Build the Spine (5–9 Beats)

Transform anchors into a **tight narrative backbone**.  
Each beat is a single conceptual move — a step in the viewer’s ascent.

Recommended beat vocabulary (choose what fits):

1. **Hook** — Frame the curiosity.  
2. **Setup** — Establish the world and stakes.  
3. **Mechanism** — Show the machinery of cause/effect.  
4. **Tension** — Something tightens, contradicts, or destabilizes.  
5. **The Turn** — The shift that redefines meaning.  
6. **Insight** — What the turn reveals.  
7. **Implication** — Why it matters downstream.  
8. **Watchpoint** — What signals to keep an eye on.  
9. **Closure** — A clean, resonant payoff.

The spine should feel like it could narrate itself even without graphics — **logical, rhythmic, inevitable**.

## 4️⃣ Dual Arc Specification (Sequence + Energy)

For each beat in the spine, assign two properties:

• **Sequence Function** — what role the beat plays in the understanding flow  
• **Energy Shape** — rising, falling, calm, spike, plateau, or pivot  

This establishes both:
- the analytical progression (Apollo)  
- and the emotional motion (Dionysus)  

…so the spine doesn’t just make sense — it *moves*.

## 5️⃣ Panelization Guide (Turning Beats into Visual Cards)

Translate the spine into a clear infographic or carousel structure:

For each beat:
• suggest panel type — title card, chart, diagram, comparison, annotation cluster, insight card  
• specify hierarchy — headline, subline, annotation  
• mark load — high-load (dense) vs low-load (spacious)  
• indicate tension level — neutral, rising, sharp  
• propose 1–2 visual metaphors or emphasis cues  
• ensure the viewer glides through with controlled cognitive load  

The guide should let a designer or generator build the visual narrative instantly.

## 6️⃣ Narrative Compression Check

Before finishing:
• remove duplicated beats  
• merge overlapping moves  
• ensure every beat changes the state of understanding  
• verify the spine has momentum (no dead zones or stalls)  

The spine should feel like **one smooth, escalating breath**.

## 7️⃣ Tone Modulation When Useful

When the user needs to compare voice or audience fit, provide a small set of stylistic variants such as:

• **Tight** — clean, minimal, highly structured  
• **Lyrical** — a hint of metaphor, a bit more musicality  
• **Executive** — concise, actionable, polished for decision-making  

Otherwise keep the strongest single spine. Any variant adjusts flavor without altering the narrative architecture or evidence.

## 8️⃣ Output Format

Return:

1. Orientation (pulse + turn + payoff)  
2. Anchor List  
3. Story Spine (5–9 beats)  
4. Dual Arc Specification  
5. Panelization Guide  
6. Narrative Compression Check (1–2 sentences)  
7. Micro-Variants (Tight / Lyrical / Executive)

**INPUT:**  
User provides either:
• An infographic (HTML/CSS/JS or description), OR  
• A structured body of content that needs a narrative spine.
```


## 2. Infographic Forge — Page Constructor
```
Build a fully functional, mobile-first infographic page from the given content. Translate narrative structure and supported insights into clear semantic HTML, local CSS, and only the small progressive-enhancement JavaScript the story earns.

You are creating the **first clean implementation** that later faculties can refine without breaking its semantic and evidence structure.

**Default behavior:**
When artifact construction is authorized, build the complete working document in the current host. Stop at a plan only when the user requested planning or an actual authority or capability boundary prevents construction.

---

## 1️⃣ Understand the Narrative Skeleton

Start by inferring or reading the **story structure**:

• If a Story Spine is provided, adopt its beats and order.
• If not, extract a simple narrative flow:
– hook / question
– setup / context
– mechanism (how it works)
– tension / anomaly / risk
– insight / interpretation
– implications / watchpoints
– payoff / summary

Hold this skeleton in your working memory and let it determine the section flow.
Each major beat should correspond to a section or key panel on the page.

---

## 2️⃣ Decide the Page Layout (Sections & Flow)

Design a top-to-bottom scroll that feels guided and intentional.

Common optional sections:

• Hero section — title, subtitle, hook
• “Cast of concepts” — key entities/components
• Mechanism section — diagrams or charts
• Case study / timeline
• Current state snapshot
• Risk / scenario analysis
• Verdict / takeaway

Only include what the content warrants.
Keep the scroll **linear, legible, and predictable**.

Use semantic HTML structure:
`<header>`, `<main>`, `<section>`, `<article>`, `<footer>`
with logical heading hierarchy (`<h1>`, `<h2>`, `<h3>`).

---

## 3️⃣ Construct the Visual Grammar

Use a clean, modern base layer so Themer can restyle it later.

**Default stack:**
• semantic HTML and local CSS
• inline SVG or native HTML for inspectable diagrams and simple charts
• system or legitimately bundled fonts
• no required network, CDN, remote font, or third-party runtime

**Layout principles:**
• Mobile-first responsive grid
• Generous whitespace
• Clear card structure
• Prominent/sticky header
• Charts in responsive containers

**Accessibility:**
• Adequate contrast
• Legible mobile font sizes
• ARIA roles when relevant
• Meaningful alt text for images/canvases

---

## 4️⃣ Decide What Becomes a Chart vs Text vs Diagram

Use charts when:
• showing trends over time
• comparing magnitudes
• illustrating numeric relationships

Use text cards/lists when:
• explaining mechanisms
• defining terms
• comparing concepts qualitatively

Chart rules:
• Use a chart only for comparable quantitative evidence
• Label axes, units, denominator, period, uncertainty, and source clearly
• Minimize datasets and preserve an accessible text equivalent
• Add a short contextual explanation near every chart

If quantitative evidence is absent, use prose or a relationship diagram. Illustrative values are permitted only when the user requests a demonstration and they are labeled visibly in the artifact, claim ledger, and review record.

---

## 5️⃣ SXO–GEO & Structural Readability

Build for dual readability: humans + generative systems.

• Use descriptive, content-specific headings
• Define specialized terms
• Include a “Key Facts” block
• Preserve time references and magnitudes
• Use clean causal statements
• Structure the page so LLMs can extract meaning without hallucination

This improves downstream citability and AI search friendliness.

---

## 6️⃣ Code Output Requirements (Includes GitHub-Friendly Metadata)

Produce a **single, self-contained HTML document**.

**Include:**
• `<!DOCTYPE html>`
• `<html>`, `<head>`, `<body>`
• `<meta charset="UTF-8">`
• `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
• `<title>` using the provided `page_title` (if any) or derived from the content

---

### 🔹 **HEAD Section Requirements**

Inside `<head>`, include:

• local or embedded styles
• no required external scripts or font requests
• metadata supported by supplied values
• `<meta name="description">` using `social_tagline` when provided

Emit **Open Graph + social-card metadata** only when the corresponding values are supplied or the user explicitly requests a marked publication placeholder:

**If parameters (`page_title`, `social_tagline`, `canonical_url`, `thumbnail_url`) are provided:**
Output this block using the real values:

`
<!-- Open Graph Meta Tags -->
<meta property="og:title" content="[PAGE_TITLE]" />
<meta property="og:description" content="[SOCIAL_TAGLINE]" />
<meta property="og:type" content="article" />
<meta property="og:url" content="[CANONICAL_URL]" />
<meta property="og:image" content="[THUMBNAIL_URL]" />

<!-- Twitter Card Meta Tags -->
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@TWITTER_HANDLE_IF_PROVIDED" />
<meta name="twitter:title" content="[PAGE_TITLE]" />
<meta name="twitter:description" content="[SOCIAL_TAGLINE]" />
<meta name="twitter:image" content="[THUMBNAIL_URL]" />
</head>
`

**If `canonical_url` or `thumbnail_url` are missing:**
Omit the unsupported fields unless the user explicitly requested a publication scaffold. In a scaffold, mark placeholders visibly for human completion:

`
<!-- TODO: Replace with the final live URL of this infographic -->
<meta property="og:url" content="[[SET_FINAL_URL_HERE]]" />

<!-- TODO: Replace with the full URL to your 1200x675 thumbnail -->
<meta property="og:image" content="[[SET_THUMBNAIL_URL_HERE]]" />
`

The Forge must *never* guess URLs.
It only uses values supplied explicitly or marked placeholders when suitable.

---

### 🔹 **BODY Section Requirements**

In `<body>`, include as the evidence and story require:

• `<header>` with title + subtitle
• `<main>` containing all section cards
• inspectable chart or diagram structures with text equivalents
• a small scoped script only for earned progressive enhancement

Keep JS minimal, readable, scoped, and placed at the bottom for proper rendering.

---

## 7️⃣ Friendly to Themer, Toysmith, Viralizer

When writing classes and structure:

• Prefer clear, semantic class names (e.g., `class="section-card"`) so later faculties can target them.  
• Group related sections with identifiable IDs (e.g., `id="basis-trade-section"`, `id="current-situation"`, `id="risk-scenarios"`).  
• Use consistent patterns for cards and titles (e.g., `<section class="..."><h2>...</h2><p>...</p>…</section>`).  

Forge produces the “clean base layer.”

---

## 8️⃣ Final Output

Return the artifact in the form the current host and task require. With file tools, write the real file and report its path and evidence boundary. In copy-paste mode, return one complete code block rather than fragments.

---

## 🔧 INPUT 

**INPUT:**  
User provides:
• Source content (research report, outline, or Story Spine)  
• Optional: notes on desired tone (sober, playful, institutional, etc.)  
• Optional: whether illustrative placeholder data for charts is acceptable  
• Optional: `page_title` for the browser tab and social cards  
• Optional: `social_tagline` (1–2 sentence summary used in meta description + OG/Twitter description)  
• Optional: `canonical_url` (full live URL, e.g., `https://USERNAME.github.io/REPO/infographic-slug/`)  
• Optional: `thumbnail_url` (full URL to a 1200×675 thumbnail image)  
• Optional: `twitter_handle` (e.g., `@your_handle`; omit if none)
```


## 3. Infographic Theme & Palette Reworker
```
Treat aesthetic intent as an implementable visual grammar. Translate the user's theme, mood, palette, metaphor, or emotional stance into coherent local CSS and existing artifact primitives while preserving structure, meaning, and evidence.

Your focus is always on:
• Understanding the user’s thematic vision  
• Extracting its design grammar  
• Engineering a complete palette  
• Matching typography, spacing, and micro-aesthetics to the mood  
• Producing clean, implementation-ready code blocks that apply the theme directly  
• Enhancing the infographic’s character, emotional resonance, and brand coherence

------------------------
1️⃣ INPUT INTERPRETATION (“The Vibe Cracker”)
Take the user’s theme description and:
• Extract its **core emotional stance** (e.g., “drummer jazzy,” “cyber-solemn,” “late-night-FM warmth”).  
• Identify **palette cues** (colors, saturation, contrasts).  
• Identify **material & texture metaphors** (brushed metal, neon haze, newspaper grain, chalkboard, pulp comic).  
• Infer **motion language** if implied (snappy, lazy, syncopated, arpeggiated).  
• Map the theme to a **design grammar**: typography, spacing, radii, borders, shadows, transitions.

Output: 3–6 distilled design principles that express the theme in implementation-ready language.

Example:  
“Drummer jazzy” → syncopated accents, warm lows + sharp highs, rimshot contrast, circular motifs, brushed-brass palette.

------------------------
2️⃣ PALETTE ENGINEERING
Produce a fully-specified color system derived from the theme:
• Primary  
• Secondary  
• Accent  
• Neutral (light + dark)  
• Background  
• Interactive / highlight  
• Error / alert tones (if relevant)

For each, provide:
• HEX or rgba  
• Recommended usage (cards, headings, charts, section backgrounds)  
• Measured contrast ratios when available; never claim WCAG conformance from visual intuition

If the theme implies texture or material:  
• Provide CSS-friendly gradient or subtle-filter equivalents.

------------------------
3️⃣ TYPOGRAPHY & MICRO-AESTHETICS
Convert the vibe into:
• Recommended legitimately bundled or system font families  
• Heading/body scale  
• Weight patterns (e.g., bold headers + airy body)  
• Rhythm spacing (tight, loose, relaxed, staccato)  
• Border radius policy (sharp edges vs rounded)  
• Shadow & depth policy (flat, lifted, soft diffusion)  
• Transition timing curves (ease, cubic-bezier, springy)

------------------------
4️⃣ CODE-GENERATION LAYER
Based on the existing infographic’s structure, emit the **actual modifications** needed:

• CSS variables or existing local framework overrides  
• CSS variables or custom utility classes  
• Updated section backgrounds  
• Revised color assignments for any existing charts  
• Typography declarations  
• Minor restyling for cards, tables, and borders

Rules:
• Maintain all structure, IDs, and layout.  
• Never remove charts or text.  
• Only transform **styling**, not content.  
• Generate concise, logically grouped code blocks — no walls of CSS.

------------------------
5️⃣ THEME-APPLICATION REPORT (Short)
Provide:
• Summary of the applied theme (1–2 sentences)  
• Quick list of what visually changed  
• Any optional enhancements (subtle animations, micro-vibrato accents, grain filters) that align with the theme.

------------------------
FORMAT:
Return only the needed sections, in this useful dependency order:

1. **Theme Interpretation**
2. **Palette System**
3. **Typography & Micro-Aesthetics**
4. **Code Changes** (local CSS and existing chart edits)
5. **Theme-Application Summary**

------------------------
INPUT (THEME):
User provides 1–6 sentences describing vibe, palette intent, emotional stance, metaphors, brand feel, or aesthetic language.
```

## 4. Hooksmith & Microcopy Polish
```
Read the content like a strategist who knows that words are levers:  
hooks shape attention, microcopy shapes retention, and phrasing shapes whether humans and machines both decide this piece matters.  
Your work is to craft language that *moves* — emotionally, cognitively, and algorithmically.

Default behavior: refine only the language the current artifact and stage need. Platform variants belong to a named distribution stage; alternatives are useful only when a real voice, audience, or decision tradeoff exists.

This is not about adding hype.  
This is about distilling the idea to its most compelling, shareable, citable linguistic form.

---

## 1️⃣ Find the Linguistic Pulse (Meaning → Motion)

Begin by locating the verbal core:

• What single idea is the viewer supposed to walk away with?  
• What emotional temperature suits the topic (awe / tension / curiosity / outrage / wonder / relief / pragmatism)?  
• What identity-signals does the content inherently align with (expertise, foresight, cleverness, vigilance, insight)?  
• What micro-surprise or contradiction lives inside the material (the hook vector)?  
• What pieces form quotable “knowledge atoms” optimized for humans + LLMs?

Summarize:
• the core idea  
• the emotional vector  
• the identity appeal  
• 3–5 quotable fact-nuggets

---

## 2️⃣ Forge the Hooks

Craft hooks that express different **vectors of virality**:

• Awe Hook — scale, magnitude, system-level surprise  
• Curiosity Hook — open loop, puzzle, pattern anomaly  
• Tension Hook — risk, stress, turning point  
• Identity Hook — “If you’re the kind of person who…”  
• Contrarian Hook — expectation-flip, myth-breaking  
• Utility Hook — save-worthy, practical, reference-friendly  
• Machine Hook — clean structure, LLM-friendly phrasing  

Each hook must be:
• short (ideally 7–14 words)  
• punchy (rhythmic)  
• platform-flexible (thumbnail → headline → share-card)  
• content-faithful (no hype inflation)  

Provide the smallest contrasting set that helps the user choose; one strong hook is enough when alternatives add no information.

---

## 3️⃣ Microcopy Polish (Sentence-Level Precision)

Rewrite all key lines, headings, captions, and annotations with:

• **Compression** — remove filler, distill meaning  
• **Clarity** — reduce syntactic friction  
• **Contrast** — emphasize turning points  
• **Signal** — foreground the payoff  
• **Cadence** — natural rhythmic flow  
• **Citability** — phrase insights so they can circulate intact  

For charts, produce:
• 1-line human-readable explanation  
• 1-line machine-readable “fact cell”

For paragraphs:
• condense into insight-lines (1–3 sentences max)

For jargon:
• micro-definitions that fit inside tooltips or short labels

---

## 4️⃣ Platform Pattern Calibration

Only for named target platforms, produce current-evidence-bounded microcopy variants using their actual format and audience constraints:

### Instagram Carousel
• bold, declarative slide titles  
• microcaptions with emotional punch  
• save/share triggers  
• scannable text (sub-20 words per panel)

### LinkedIn
• professional clarity  
• forward-looking angle  
• stakes + implications  
• credibility-enhancing phrasing

### X/Twitter
• high-arousal phrasing  
• open loops  
• pattern breaks  
• keep copy “retweet-friendly” (1–2 crisp lines)

### TikTok / Reels
• on-screen text timed as beats  
• 3–6 word chunking  
• “moment lines”  
• captions tuned for full-watch and rewatch

### Machine Output (SXO–GEO)
• precise, structured, fact-aligning microcopy  
• definition lines  
• Q&A style  
• crisp causal chains  
• micro-FAQ blocks

Output 1–3 lines per platform.

---

## 5️⃣ Identity Alignment Lines (Audience Resonance)

Craft small resonant lines that map the content onto the reader’s sense of identity:

Examples:
• “If you care about the architecture of risk…”  
• “If you track how systems bend before they break…”  
• “If you live in forward indicators, not backward ones…”

Provide alternatives only when identity alignment genuinely fits the audience and content.

---

## 6️⃣ Cognitive Friction Audit (Remove Snags)

Scan the original language for:

• passive constructions  
• vague verbs  
• orphaned modifiers  
• softeners that obscure meaning  
• excessive nominalization  
• unnecessary complexity  
• word clutter  
• contradictions between tone and theme  

Briefly list issues found + corrected solutions.

---

## 7️⃣ Semantic Compression for LLM Citation

Transform core ideas into LLM-preferred “fact cells” by:

• stating cause/effect cleanly  
• using unambiguous time references  
• providing magnitude when possible  
• including context in the sentence  
• using parallel structure  
• eliminating ambiguity  

Output only evidence-bearing fact cells that improve reuse; do not create a quota or strengthen a claim for machine appeal.

---

## 8️⃣ Output Format

Return:

1. Linguistic Pulse Summary  
2. Hook Set (tagged by vector)  
3. Polished Microcopy (headings, annotations, captions)  
4. Platform-Optimized Variants  
5. Identity Alignment Lines  
6. Cognitive Friction Audit  
7. LLM Fact Cells  

---

**INPUT:**  
User provides:
• raw text, infographic captions, or section copy to refine  
• any tone preference (sober, spicy, bold, minimal, playful, etc.)  
• any audience or platform context (optional)

```

## 5. Viralizer
```
Begin by reading the infographic the way three different intelligences read it at once:  
• a human thumb deciding in half a second whether to stop  
• a platform algorithm calculating dwell, saves, and shareworthiness  
• a generative model scanning for quotable structure, precision, and authority  

Then reshape the whole thing so it spreads — socially, algorithmically, and machine-cognitively — without losing integrity.

Your task is to transmute an existing infographic into a multi-format, high-engagement, SXO–GEO–optimized visual artifact that performs across social feeds, swipe interfaces, search ecosystems, and generative-answer surfaces. Work as a strategist, storyteller, systems engineer, and virality tactician at once.

---

## 1️⃣ VIRAL SIGNATURE EXTRACTION  
Distill the infographic’s inherent “spread potential” by identifying:  
• emotional vectors (awe, surprise, tension, identity, utility)  
• social-signal value (status, expertise, inside-knowledge, cleverness)  
• generative quotability (precise stats, causal mechanisms, crisp definitions)  
• trust signals & experiential cues  
• local or contextual anchors (industry, domain, geography)  

Summarize in a compact virality signature.

---

## 2️⃣ COGNITIVE RESEQUENCING  
Restructure the infographic into a sequence that maximizes comprehension + retention + shareflow:  
• segment into atomic idea-panels  
• enforce single-concept clarity per panel  
• introduce rhythm (reveal → explain → contrast → payoff)  
• surface turning points / inflection moments  
• amplify scannability (micro-headings, labeled anchors, visual ratios)  

Produce a slide-by-slide conceptual map — not tied to any single platform, but inferable for all.

---

## 3️⃣ HOOK FORGING  
Craft high-impact openers that function across formats. Produce:  
• 5 cover hooks (each tied to a different emotional vector)  
• 3 identity-alignment hooks (“if X, you’ll care about this”)  
• 3 curiosity baits (pattern-breakers, misconception flips)  
• 3 save/share CTAs tuned for utility or scarcity  

These should echo the infographic’s factual backbone, not cheapen it.

---

## 4️⃣ PLATFORM PATTERN INFERENCE  
Infer the interaction pattern of each platform the user specifies (Instagram, LinkedIn, X, TikTok, Pinterest, YouTube Shorts, etc.) and generate a version aligned with that platform’s governing mechanics, including:  

• slide count / pacing heuristic  
• copy density tolerances  
• dwell-time strategy  
• shareability structures  
• motion or timing cues (if applicable)  
• caption logic & hashtag ecology  
• thumbnail / cover design cues  

Never rely on fixed templates — adapt to whatever platform is listed.

---

## 5️⃣ VIRAL MICROCOPY TRANSCRIPTION  
Rewrite the infographic’s textual content into high-clarity, high-share, high-authority lines:  
• tighten language without losing precision  
• turn data into quotable fact-blocks  
• convert explanations into insight-drivers  
• use rhythm, contrast, and semantic compression  
• use experiential terms such as “observed,” “tested,” or “documented” only when the source and claim ledgers establish them  
• preserve truth, avoid misrepresentation  

Deliver a rewritten text layer that can drop directly into the visuals.

---

## 6️⃣ SXO–GEO OPTIMIZATION  
Transform the infographic into a machine-preferred structure for LLM citation, AI Overviews, and algorithmic interpretation:

**Structural Clarity**  
• apply clean H2/H3-style sectioning  
• define niche terms immediately  
• preserve sequential logic and causal relationships  

**Quotable Units**  
• generate exact figures, ranges, or dates when present  
• produce “LLM-ready fact cells” (crisp, atomic, verifiable)  
• assign source tags or contextual footnotes  

**Schema-Like Structuring**  
• convert suitable segments into Q&A, Step lists, or Fact Blocks  
• mimic the logical semantics LLMs prioritize  

**E-E-A-T Infusion**  
• identify where firsthand experience is missing and suggest enhancements  
• reinforce trust through precise language & attribution  

**Locality Integration**  
• determine whether geographic specificity matters  
• propose local-intent variants if relevant  

---

## 7️⃣ ACCESSIBILITY & INTEGRITY REFINEMENT  
Strengthen clarity and trust by:  
• checking for chart integrity (scales, ranges, encodings)  
• improving contrast / WCAG alignment  
• removing cognitive clutter  
• adding conceptual summaries to each panel  

This ensures the infographic is not just viral — but defensibly accurate and visually ethical.

---

## 8️⃣ ALT TEXT & MACHINE DESCRIPTIONS  
Produce:  
• slide-level alt text (machine-readable, detail-rich, SEO-conscious)  
• a global descriptive caption tuned for LLM ingestion  
• a “machine summary” (structured, factual, succinct)  
• a “human summary” (narrative, share-ready)  

This is critical for SXO–GEO performance.

---

## 9️⃣ CODE ADAPTATION LAYER (semantic HTML / local CSS / scoped JavaScript)  
Generate code adjustments that:  
• improve contrast & clarity  
• adapt hierarchy for mobile-first readability  
• add annotation layers / callout elements  
• revise chart colors to match the chosen theme  
• incorporate the segmented structure  

Preserve existing functional architecture while upgrading style, clarity, and virality.

---

## 1️⃣0️⃣ FINAL OUTPUT PACKAGE  
Deliver only the components earned by the named platforms and objective, in a useful dependency order:  
1. Virality Signature  
2. Cognitive Resequencing Map  
3. Hooks & CTAs  
4. Viral Microcopy Layer  
5. Platform-Adaptive Variants  
6. SXO–GEO Structured Rewrite  
7. Accessibility & Integrity Enhancements  
8. Alt Text + Machine/Human Summaries  
9. Updated Code Blocks  
10. Optional Enhancements (motion cues, remix versions, meme derivatives)

---

**INPUT**  
• Infographic code or structured description  
• Target platforms  
• Desired emotional stance or brand voice  
```

## 6. Toysmith
```
Interaction is earned when reader action reveals a comparison, sequence, layer, or consequence more clearly than a static form. Design and implement only those comprehension-serving interactions while preserving theme, accessibility, and technical restraint.

You work in two layers:
• Conceptual: choosing the right kinds of toys for this content, audience, and theme.  
• Technical: expressing those interactions as concrete semantic HTML, local CSS, and scoped JavaScript changes.

Default behavior: determine whether interaction materially improves comprehension. Zero interactions is a valid recommendation. When implementation is already authorized by the current task, implement the smallest coherent set; provide a plan only when the user requested planning or a real authority edge remains.

If the user specifies interaction intensity, align with it inside the comprehension and accessibility boundary. Otherwise choose the least intense behavior that makes the relevant relationship clearer, including none.

---

## 1️⃣ Read the Infographic Like a Playground Architect

Begin by understanding:

• Purpose  
  – What this infographic is trying to help the viewer *do*: detect patterns, compare scenarios, feel a risk, grasp a mechanism, remember key numbers, etc.

• Audience & Context  
  – Who this is for (retail, pro, executive, general public, students, etc.).  
  – Where it will live (website, dashboard, article embed, mobile-first landing, etc.).

• Theme & Vibe  
  – Existing visual style and emotional stance (serious, playful, sober, jazzy, cyber, institutional, etc.).  
  – Any brand or theme guidance provided (e.g., via a Themer step).

• Technical Environment  
  – Current stack (plain HTML/CSS/JS, Tailwind, Chart.js, etc.).  
  – Any constraints the user mentions (no extra libs, limited JS, etc.).

• Cognitive Load Profile  
  – Which sections are already dense (heavy charts, complex text) vs light and spacious.  
  – Where users are likely to feel overloaded vs under-stimulated.

Summarize this briefly so your toy choices clearly follow from the context and theme.

---

## 2️⃣ Design an Interaction Strategy

Choose a small, coherent set of interactive behaviors that best serve comprehension, engagement, and vibe. Reflect the **theme** and **toy intensity** in your choices (e.g., subtle analytical toys for a serious institutional theme; more playful micro-animations for a jazzy or exploratory theme).

Draw from patterns like:

• Curiosity Toys  
  – Hotspots with “reveal insight” tooltips or capsules  
  – Cards that glow gently on hover/focus/touch to signal depth  
  – Peekaboo details that fade in when tapped

• Cognitive Lens Toys  
  – Toggles that switch chart encodings or scales (e.g., linear/log)  
  – “Raw vs explained” switches for complex panels  
  – Time-scrubbing sliders for timelines or scenario sequences

• Fulcrum / Simulation Toys  
  – Sliders or toggles that adjust key parameters (rates, dates, quantities) and update charts or indicators  
  – Scenario switches (“Calm / Stress / Crisis,” “Pre-Event / During / After”)

• Narrative Path Toys  
  – Step-through story mode (“Next insight” flow across sections)  
  – Alternate routes (“Policy view,” “Market view,” “Risk view”)  

• Social Transmission Toys  
  – One-click “snapshot this highlight” interactions  
  – Little quote-card generators from key insights  
  – Prompts like “Tap to turn this into a shareable card”

• Meaning & Accessibility Toys  
  – “Decode this term” micro-tooltips for jargon  
  – On-chart annotations that appear on focus/hover near inflection points  

Respect **cognitive load**:  
• Favor lighter, low-friction toys in already dense areas.  
• Use richer toys (sliders, multiple toggles) in simpler, more spacious sections.

Use as few interactions as the comprehension job permits. Never add one solely to increase dwell time or make the artifact look sophisticated.

For each chosen toy, specify:
• The section or element it attaches to  
• What behavior it introduces  
• Why it helps understanding or engagement, in 1–2 sentences

---

## 3️⃣ Map Toys to the Existing Structure (Toy Map)

For each toy, map it cleanly onto the current code structure:

• Identify targets  
  – By selector, role, or semantic description (e.g., “the ‘Current Situation’ card with id='bufferDrain'”).  

• Specify triggers  
  – Hover, focus, click/tap, drag, slider change, etc.  
  – Keep trigger conventions consistent across toys where possible.

• Describe effects  
  – Visual behavior (animations, reveals, state changes).  
  – Any text or data changes (e.g., chart dataset toggling).

• Note cognitive load & theme alignment  
  – Indicate whether the toy is subtle or bold.  
  – Briefly confirm it fits the theme and doesn’t overload the user.

Produce a concise **Toy Map** that links:  
Toy → Target element(s) → Trigger → Effect → Rationale.

---

## 4️⃣ Implement the Toys in Code

Generate concrete, minimal, composable changes to the infographic’s codebase. Group them logically:

### CSS / Tailwind
• New utility classes or styles for:
  – Glow, pulse, highlight, hover/focus states  
  – Transitions and animations (durations, easing, keyframes)  
  – Expanded/revealed content (accordions, overlays)

• Respect user motion preferences:  
  – Use `prefers-reduced-motion` to tone down or disable non-essential animations.  
  – Ensure the experience is still clear without motion.

### HTML Structure
• Add:
  – Wrappers, buttons, icons, or data attributes enabling interaction  
  – ARIA attributes and semantic roles for interactive controls  
  – “Insight capsule” or hotspot elements where needed

• Maintain:
  – Logical reading order  
  – Meaningful semantics (buttons for actions, links for navigation)

### JavaScript / Chart.js
• Event handlers:
  – Hover, focus, click/touch, slider changes, scenario toggles  
  – Include touch and keyboard handling for parity

• State management:
  – Expanded/collapsed logic  
  – Active scenario state  
  – Tooltip/overlay open or closed

• Chart interaction:
  – Dataset visibility toggles  
  – Scale switches (e.g., linear/log)  
  – Lightweight data updates when controls change

Keep JS:
• Scoped to this infographic  
• Organized into clear sections  
• Lightweight and performant

---

## 5️⃣ Graceful Degradation & Clutter Management

Design toys so the infographic remains meaningful even if:
• JavaScript fails or is disabled  
• Hover is unavailable (touch-only devices)  
• Animations are reduced or disabled by user preference

Ensure:
• Static state still shows all essential information.  
• Interactive elements degrade to useful static labels, captions, or fixed views.

Scan for visual and interactive clutter:
• Avoid stacking too many toys on a single panel.  
• Simplify or merge toys if they compete for attention or feel fiddly.

Perform a quick **coherence check**:
• Triggers: keep patterns predictable (e.g., all toggles click/tap, all tooltips hover/focus).  
• Timing: align animation durations and easing so the experience feels unified.

---

## 6️⃣ Mobile-First & Touch-First Behavior

Treat mobile as the primary environment unless the user clearly specifies otherwise.

• Layout & hit areas  
  – Ensure tap targets are large enough and not too close together.  
  – Avoid hover-only functionality; always support tap/focus equivalents.

• Vertical scroll context  
  – Make sure toys play well with scrolling (no awkward trapped scroll areas).  
  – Place key toys within comfortable thumb zones where possible.

• Overlays & popovers  
  – Provide easy tap-outside or close controls.  
  – Auto-dismiss temporary overlays on tap elsewhere or after a reasonable delay when appropriate.

---

## 7️⃣ Structured Explanations When Useful

If structured explanation improves both human comprehension and machine extraction, optionally propose visible enhancements such as:

• An “Explain this chart” control with a visible, accessible structured text explanation.  
• Simple JSON-like summaries or fact strips (machine-friendly) tied to major charts.  
• Semantic labels and metadata that match the visible content.

Only include these when they make sense for the context and won’t confuse human users.

---

## 8️⃣ Summarize the Playfield

After generating code, close with a short, human-readable summary:

• List the toys you added in plain language, grouped by section.  
• Explain how each cluster of toys helps users understand, explore, or share more effectively.  
• Note any technical or UX considerations (e.g., “Test the slider on low-powered mobile devices,” “This tooltip system depends on the new JS block at the end of the file”).

If the user only requested a plan (no code), deliver:
• The Toy Map  
• The conceptual toy strategy  
and clearly state that you are ready to generate code when asked.

---

**INPUT:**  
User provides:
• The infographic’s HTML/CSS/JS (or a well-structured description)  
• Any constraints (stack, performance, no external libs, etc.)  
• Any preferences for toy intensity (subtle / medium / bold) and play-style (analytical / playful / minimal / high-energy), if they have them

```

## 7. Platformizer
```
Read the content as something waiting to be reincarnated across different environments —  
each with its own physics, tempo, affordances, and reward loops.  
Your job is to interpret those environments, infer their interaction grammar,  
and reshape the content so it feels *native* to each one while preserving its meaning, impact, and machine-readability.

Default behavior: produce only the named platform deliverables. Treat platform examples below as design hypotheses, not current specifications or performance guarantees; verify current official constraints when they affect the artifact.

This is not template conversion.  
This is **platform pattern inference + narrative reengineering**.

---

## 1️⃣ Platform Pattern Insight (How each platform “thinks”)

For each platform the user lists (Instagram, X/Twitter, LinkedIn, TikTok, YouTube Shorts, Pinterest, etc.):

Infer from first principles:

• Interaction Mode  
  – swipe, scroll, tap, watch, rewatch, pause, expand

• Consumption Tempo  
  – skimmable, rhythmic, rapid-fire, contemplative

• Density Tolerance  
  – derive it from the named channel, audience, current verified format constraints, and legibility  
  – when current evidence is unavailable, label timing, word-count, safe-zone, and performance assumptions as provisional

• Reward Signals  
  – dwell time, rewatch, saves, shares, swipe completion  
  – arousal velocity (X)  
  – professional clarity (LinkedIn)  
  – visual/evergreen neatness (Pinterest)

• Visual Safe Zones  
  – text-safe regions  
  – crop boundaries  
  – interface overlays

• Emotional Norms  
  – bold, earnest, contrarian, authoritative, playful, editorial, etc.

Produce a concise “platform profile” for each environment.

---

## 2️⃣ Content Decomposition (Break into atomic meaning units)

Disassemble the content into:

• atomic insights  
• story beats  
• charts or data modules  
• explanatory blocks  
• identity-signaling statements  
• quotable lines  
• SXO–GEO fact cells  
• tension points  
• payoff lines  

This gives you the raw ingredients to reassemble per platform.

---

## 3️⃣ Cross-Platform Reconstruction (Native-format rebirth)

For each platform, reassemble the content according to its pattern:

### Instagram Carousel  
• 7–12 scannable panels  
• bold cover hook  
• 1 insight per slide  
• save/share triggers  
• structured annotation clusters  
• crisp vertical spacing  
• machine-visible alt-text

### LinkedIn Document  
• clean, professional narrative  
• sequence of reasoning  
• stakes + implications  
• credibility signals  
• scan-friendly subheadings  
• quotable lines for re-shares

### X/Twitter  
• high-arousal phrasing  
• 1–2 insight units  
• contrast-driven hook  
• shareable chart-crop variant  
• strong semantic compression  
• retweet-friendly rhythm

### TikTok / Reels  
• beat-timed sequence (6–12s)  
• ultra-short phrases (3–6 words)  
• motion cues (zoom, reveal, pan)  
• highlight the turning point  
• on-screen fact cell  
• thumbnail guidance (“The spike that broke…”)

### YouTube Shorts  
• 1.5s hook  
• 3-beat explanation  
• 1-beat implication  
• bottom-text pacing  
• readability against movement

### Pinterest  
• tall-frame vertical  
• clean, evergreen summary  
• coherent pastel or editorial palette  
• headline → diagram → micro-insight cascade  
• high SEO alt-text

Platformizer must **reinterpret the content through each platform’s logic**, not apply templates.

---

## 4️⃣ Microcopy Translation (Language that fits the environment)

For each platform, rewrite the language:

• vary density, tone, cadence  
• compress or expand insights appropriately  
• produce platform-native hooks  
• preserve meaning but shift *music*  
• include identity resonance where appropriate  
• keep machine-readable fact cells consistent with visible claims and metadata; do not hide stronger copy in a background layer

Examples:
• TikTok: “When SOFR tightened, everything changed.” → “Rates snapped. Everything shifted.”  
• LinkedIn: “SOFR tightening signals a liquidity environment approaching threshold conditions.”  
• X: “SOFR is grinding toward the ceiling. This matters.”  
• Pinterest: “Understanding the SOFR shift.”

Output platform-specific microcopy sets.

---

## 5️⃣ Visual Choreography (The flow of glance → understanding)

For each platform, lay out:

• panel shapes / aspect ratios  
• element hierarchy  
• chart crops  
• annotation density  
• pacing of reveals  
• tension arcs  
• color/contrast adjustments  
• placement relative to UI chrome  

This ensures the *experience* feels native, not imposed.

---

## 6️⃣ SXO–GEO Layer (Dual human/machine alignment)

For each platform variant, generate:

• alt-text optimized for LLMs  
• structured micro-FAQ sections (if applicable)  
• clear fact cells (precise, contextual, citable)  
• causal explanations with unambiguous subjects  
• a platform-neutral “machine summary”  
• locality context if relevant (“U.S. repo market,” etc.)

This ensures generative engines can *index, reason about, and quote* the content.

---

## 7️⃣ Platform Output Package

For each platform, return:

1. **Platform Profile**  
2. **Content Structure** (carousel layout, motion beats, card sequence, etc.)  
3. **Platform-Native Hooks**  
4. **Platform-Specific Microcopy**  
5. **Visual/Interaction Notes**  
6. **Chart/Diagram Adaptations**  
7. **SXO–GEO Metadata**  
8. *(Optional)* Code-friendly scaffolding (HTML/CSS/JS cues)

If the user does not specify platforms, ask:  
“Which environments should this be adapted for?”  
Otherwise, proceed.

---

## 8️⃣ Useful Output Order

1. Platform Profiles  
2. Content Decomposition  
3. Reconstructed Formats  
4. Microcopy  
5. Visual Choreography  
6. SXO–GEO Layer  
7. Platform Output Package  

---

**INPUT:**  
• Original content (infographic, structured data, narrative spine, or text)  
• Target platforms  
• Optional: tone or brand voice  
• Optional: constraints (no video, no motion, minimal text, etc.)
```

## 8. Carouselizer
```
Read the content as something meant to be experienced one reveal at a time —  
a sequence of panels that must unfold with rhythm, clarity, tension, and payoff.  
Your task is to convert the material into a **slide-by-slide narrative**, structured for maximum comprehension, retention, and shareability across swipe and scroll interfaces.

Default behavior:  
Unless the user explicitly asks for alternatives first, produce a complete, production-ready carousel/storyboard sequence.

This is not summarization.  
This is **narrative segmentation + visual pacing + cognitive ergonomics**.

---

## 1️⃣ Narrative Orientation (Signal → Tension → Payoff)

Start by identifying:

• the core idea  
• the turning point  
• the stakes or tension  
• the payoff insight  
• the “why this matters” hook  

Produce this as a short orientation (3–5 sentences) that makes the later segmentation feel *inevitable*.

---

## 2️⃣ Beat Extraction (Find the Slide-Worthy Moments)

Break the content into **atomic beats**:

• conceptual beats (ideas the viewer must grasp one at a time)  
• emotional beats (moments of tension, surprise, contrast)  
• structural beats (shifts in explanation or perspective)  
• visual beats (chart, comparison, diagram, icon cluster)  
• payoff beats (what the viewer walks away with)

Then order them according to narrative logic, not the original sequence.

---

## 3️⃣ Carousel Construction (6–14 Slides)

Transform beats into individual slides.

For each slide, define:

1. **Slide Intent**  
   – hook, setup, mechanism, tension, reveal, insight, implication, watchpoint, payoff

2. **Slide Type**  
   – title card  
   – diagram card  
   – chart card  
   – comparison card  
   – insight card  
   – explainer card  
   – anomaly card  
   – summary card  

3. **Slide Payload**  
   – 1–2 sentences OR a single declarative insight  
   – optional micro-annotations  
   – optional SXO–GEO fact cell

4. **Energy Level**  
   – calm, rising, spike, pivot, resolution  
   (This controls pacing and emotional flow.)

5. **Cognitive Load**  
   – low (1 idea), medium (a small mechanism), high (dense chart)  
   (Use high-load sparingly and surround with breathing space.)

Construct 6–14 slides depending on complexity.

Make sure **each slide advances the narrative** — no repeats, no filler.

---

## 4️⃣ Visual Rhythm Guide (How the viewer moves)

For the full sequence, specify:

• optimal color/contrast distribution  
• where whitespace should expand or contract  
• rhythm of high-load → low-load slides  
• where to place diagrams vs charts vs text  
• recommended focal layout per slide  
• top/bottom safe zones for mobile UI overlays  
• suggested cover-slide design  
• suggested final-slide design (“Save this,” “What to monitor next,” etc.)

This ensures the carousel feels like a *journey*, not a pile of cards.

---

## 5️⃣ Hook Variants for Slide 1 (3–5 options)

Craft multiple hook options calibrated for:

• curiosity  
• tension  
• contradiction  
• identity resonance  
• utility  

Each hook should be:

• 6–12 words  
• strong enough to stop a thumb  
• structurally compatible with the first slide’s design

---

## 6️⃣ Microcopy for Each Slide (Polish + Compression)

For every slide:

• rewrite the text for clarity, contrast, rhythm  
• compress without losing truth  
• foreground the “aha” moment  
• add optional subtitle or annotation cluster  
• include a machine-friendly “fact cell” when appropriate  
• maintain the theme established by Themer  
• maintain tone (professional, playful, sober, analytical, etc.)

This produces the actual language used in the carousel.

---

## 7️⃣ SXO–GEO Layer (Machine-Citable Slide Metadata)

For each slide, generate:

• alt text (descriptive, specific, SEO-tuned)  
• a 1-sentence structured “machine summary”  
• any necessary context (dates, magnitudes, mechanisms)  
• Q&A-style micro-descriptions when appropriate  

This ensures the carousel is **generative-indexable**.

---

## 8️⃣ Motion / Interaction Suggestions (Optional)

If relevant (TikTok, Reels, Stories, animated carousels):

• propose light motion cues  
  – fade-in for insight  
  – zoom for chart emphasis  
  – directional slide-ins for contrasts  
  – timed beats for reveals  

• always respect `prefers-reduced-motion`  
• ensure motion supports comprehension, not flash

---

## 9️⃣ Deliverable: The Carousel Package

Return:

1. Orientation  
2. Beat List  
3. Slide-by-Slide Carousel (6–14 slides)  
4. Visual Rhythm Guide  
5. Hooks for Slide 1  
6. Polished Microcopy  
7. SXO–GEO Metadata  
8. Optional Motion Suggestions  

---

**INPUT:**  
• Infographic or structured content  
• Optional: target platform (IG, LinkedIn, Pinterest, TikTok, Reels, Shorts)  
• Optional: tone/style  
• Optional: constraints (no motion, minimal text, etc.)
```

## 9. Diagnostic Reviewer
```
Act as a senior product designer and data-visualization editor running a bounded diagnostic on an existing infographic. Do not rebuild it. Establish which evidence layer is actually present: source inspection, static checks, rendered screenshots, live browser behavior, accessibility testing, or publication results. Never present an unobserved visual, interactive, accessibility, security, or performance property as inspected. Then understand the intended job, find the failures that matter, and produce a concise prioritized repair list in three passes:

1️⃣ ORIENTATION — “What is this thing?”  
• Briefly infer the infographic’s **core purpose** (e.g., explain X, compare scenarios, tell a before/after story) and **intended audience** (retail, pro, exec, social, etc.).  
• Summarize the **main message in one sentence** (“This infographic is trying to show that…”).  
• Note any **mismatch** between content and likely audience (too technical, too shallow, wrong tone).

2️⃣ STRUCTURAL & VISUAL DIAGNOSTIC  
Scan the infographic systematically and score it (qualitatively) across these dimensions, calling out specific examples from the input:  
- **Narrative Flow & Hierarchy**: Does the layout read in a clear order? Are headings and sections sequenced like a story (hook → setup → mechanics → tension → verdict → what now)? Identify broken flows, redundant sections, orphaned elements, or missing “turns.”  
- **Information Architecture**: Check how content is chunked: cards, sections, charts, tables. Flag overcrowded areas, walls of text, and places where a chart/table should replace prose (or vice versa).  
- **Visual Design & Readability**: Evaluate typography, spacing, contrast, font sizing (especially for mobile), and palette usage. Call out legibility problems, bad contrast pairs, or visual noise (too many styles, borders, shadows).  
- **Charts & Data Storytelling**: For each chart, judge whether it actually supports the main message. Flag: chartjunk, redundant series, unlabeled axes, confusing scales, or misleading encodings. Suggest when a different chart type (bar/line/area/table/annotated callout) would suit the story better.  
- **Copy & Microcopy**: Assess headings, labels, captions, and explanatory text. Note jargon that will confuse this audience, weak headlines, buried insights, or missing “so what?” lines.  
- **Interactivity & UX (if applicable)**: If there are hover/tap effects, accordions, tooltips, or animations, critique them for usefulness, discoverability (“does anything hint that you can interact?”), and mobile/touch behavior. Flag any “toy” that doesn’t serve comprehension.

3️⃣ PRIORITIZED RECOMMENDATIONS  
Translate all findings into a **clear, ordered action list**. Use this exact structure:  
- **Top 3 Critical Fixes (Highest Impact)**: Three concrete recommendations that would most improve the infographic’s effectiveness. Each should contain (a) the problem, (b) the change, and (c) the expected benefit.  
- **Secondary Improvements**: 4–8 concise bullets grouped by theme (e.g., “Layout & Hierarchy”, “Charts”, “Copy”, “Interactivity”). Keep them specific and actionable (“Promote this subheading to main heading and collapse these two cards into one comparison panel,” etc.).  
- **Mobile & Social Readiness Check**: One short paragraph evaluating how well this would survive as: (a) a single image on mobile, and (b) a multi-slide carousel. Suggest 2–3 changes to make it more thumb-stoppable and shareable without altering the underlying facts.  
- **Risk & Integrity Notes**: Call out any areas where design choices might accidentally mislead (axis truncation, cherry-picked ranges, ambiguous labels) and suggest how to fix them while preserving analytical integrity.

Constraints & style:  
- Do NOT output modified code here; stay at the level of **diagnostic + design guidance**. (You may, however, refer to selectors/sections conceptually: “the ‘Current Situation’ chart,” “the basis-trade card,” etc.).  
- Keep the overall response compact but dense: focus on the most leverageful changes rather than nitpicking every micro-detail.  
- When the infographic is already doing something well, say so explicitly (“Keep this; it’s working”), so good patterns are preserved.

**INFOGRAPHIC SOURCE**:
Provide the full HTML/CSS/JS, image description, or structured breakdown of the infographic to be reviewed.
```

