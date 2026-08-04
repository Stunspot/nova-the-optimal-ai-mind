# [REFERENCE] - Infographic Toolkit User's Guide

Turn dense research into actually good infographics, carousels, and social content — without touching Figma.

This guide shows you **how to actually drive the system**:

- How to load the toolkit into ChatGPT / Gemini  
- How to go from “big messy research blob” → clean web infographic  
- How to chain tools together  
- How to publish to the web with GitHub Pages (with proper social previews)

If you just dropped the `.md` file into a chat and said **“Run this”** — you’re in the right place.

---

## 0. Mental Model: What You’re Holding

The Infographic Toolkit is a **single Markdown file** that contains **9 tools**:

1. **Story Spine Builder** – turn chaos into a clean narrative backbone  
2. **Infographic Forge** – turn that backbone into a real HTML page  
3. **Themer** – reskin the visuals: palette, typography, micro-aesthetics  
4. **Hooksmith** – fix the words: hooks, captions, microcopy  
5. **Viralizer** – optimize an infographic for feeds + SXO–GEO  
6. **Toysmith** – add interactivity and toys (sliders, reveals, toggles)  
7. **Platformizer** – rebuild the same idea as **native formats** per platform  
8. **Carouselizer** – build a slide-by-slide carousel/storyboard  
9. **Diagnostic Reviewer** – critique and prioritize fixes for existing infographics  

The file also contains a **System Context** header that tells the model:

- What tools exist  
- How to pick the right one  
- What to do if you just say **“Run this”**

You do **not** need to micro-manage the tools at first.  
You can grow from **“newb autopilot”** to **“precision chaining”** as you go.

---

## 0.1 Tool Quick Reference (Cheat Sheet)

Use this as your mental API surface. Each tool is a “mode,” not just a function.

**1. Story Spine Builder**  
- **Use When:** You have a big blob (report/notes/transcript) and need a clear narrative backbone.  
- **Input:** Research report, long-form content, or infographic description.  
- **Output:** Orientation, core anchors, 5–9-beat story spine, panelization guide, variants (tight/lyrical/executive).

**2. Infographic Forge — Page Constructor**  
- **Use When:** You’re ready to turn a story spine or structured content into a real web infographic page.  
- **Input:** Story spine or structured content; optional `page_title`, `social_tagline`, `canonical_url`, `thumbnail_url`, `twitter_handle`.  
- **Output:** Full HTML page (Tailwind + optional Chart.js) with SXO–GEO structure and social meta tags/TODOs.

**3. Infographic Theme & Palette Reworker (Themer)**  
- **Use When:** The layout is fine but the aesthetic is generic or off-brand.  
- **Input:** Existing infographic HTML + a theme/vibe description (words, metaphors, palette intent).  
- **Output:** Theme interpretation, palette system, typography/micro-aesthetics, concrete CSS/Tailwind/Chart.js code changes.

**4. Hooksmith & Microcopy Polish**  
- **Use When:** The visuals are fine but the **words** (titles, captions, hooks) are mid.  
- **Input:** Headings, captions, annotations, or raw text from the infographic; optional tone + platform hints.  
- **Output:** Hooks (by vector), polished microcopy, platform-specific lines, identity alignment lines, LLM fact cells.

**5. Viralizer**  
- **Use When:** You have a specific infographic and want it to *perform* better across feeds/search/LLMs.  
- **Input:** Infographic HTML or structured breakdown; target platforms; voice hints.  
- **Output:** Virality signature, resequenced flow, hooks/CTAs, viral microcopy layer, platform-adaptive variants, SXO–GEO rewrite, alt text, code tweaks.

**6. Toysmith**  
- **Use When:** You want to add *meaningful* interactivity (sliders, reveals, toggles) to deepen understanding.  
- **Input:** Infographic HTML; toy intensity (subtle/medium/bold); vibe + constraints.  
- **Output:** Toy strategy, Toy Map, and optional concrete HTML/CSS/JS upgrades.

**7. Platformizer**  
- **Use When:** You want to take a core idea and **rebirth it natively** for IG, X, LinkedIn, TikTok, Shorts, Pinterest, etc.  
- **Input:** Core content (infographic, spine, report); target platforms; tone/constraints.  
- **Output:** Platform profiles, platform-native hooks, structure per platform, microcopy, visual choreography, SXO–GEO metadata.

**8. Carouselizer**  
- **Use When:** You want a **6–14 slide swipe sequence** (IG carousel, LinkedIn doc, Pinterest stack).  
- **Input:** Infographic or structured content; optional target platform + tone.  
- **Output:** Orientation, beat list, slide-by-slide plan, microcopy, alt text & machine summaries, motion suggestions.

**9. Diagnostic Reviewer**  
- **Use When:** You already have an infographic (or Gemini auto-infographic) and want to know what’s wrong + what to fix first.  
- **Input:** Infographic HTML/CSS/JS, image description, or structured breakdown.  
- **Output:** Orientation, structural/visual diagnostic, Top 3 critical fixes, secondary improvements, mobile/social readiness, integrity notes.

---

## 1. Typical Starting Point

Most of the time you’re starting from something like:

- A **Gemini Deep Research** report  
- A **ChatGPT / Claude research output**  
- A stack of notes, transcripts, or sales data  
- A report pasted in from Google Docs / Notion / etc.  

You already did the thinking.  
Now you want a **visual artifact** that doesn’t look like “2011 PowerPoint template” energy.

That’s where this Toolkit lives.

---

## 2. Loading the Toolkit into a Model

You generally use the Toolkit as a **drop-in file**:

### 2.1 In ChatGPT / Claude / similar

1. Start a **new chat**.  
2. Upload / attach the `Infographic Prompts v1.x.md` file.  
3. Then say something like:  
   - **“Run this.”**  
   - or **“Run this on the report I just gave you.”**  
4. Paste or upload your **source material** (report, notes, etc.) if it’s not already in the thread.

The System Context at the top of the file tells the model:

> If user says “run this” with no specific tool →  
> either:  
> - start with **Story Spine Builder** if it’s clear they want an infographic, or  
> - explain what tools exist and ask how to help.

So for first-time users, you can literally:

> drop file → “Run this on the research above.”

…and let it start with a Story Spine.

---

### 2.2 In Gemini (with or without “Create Infographic”)

You have two main modes:

#### A. **From Deep Research → Toolkit directly**

1. Run a **Deep Research** in Gemini.  
2. When you get the long-form answer, copy it or export to Docs.  
3. Start a **new chat**.  (This is mostly if you want to do your writing on another model.)
4. Paste the Infographic Toolkit `.md` into the chat, or upload it as a file.  
5. Paste the research (or attach the Doc) and say:

> "Run this on the attached report."

or even

> “Use the Infographic Toolkit from the file above.  
> Start with Story Spine Builder on this research, not a generic summary.”

That phrasing helps Gemini respect the toolkit instead of free-styling *(though honestly it's a bit overkill. --stun)*.

#### B. **From “Create Infographic” canvas → Toolkit**

1. In Gemini, hit **“Create Infographic”** on a report.  
2. Gemini will give you a mid-grade canvas.  
3. Drop the toolkit file into chat and say "Run this on that infographic." or "Run the themer on this." or whatever.

With an infographic already extent, you may or may not wish to run the story spine builder. If anything changes, Gemini will just rework things. 

This is the “rescue mission” path when Gemini’s auto-infographic is mid.

---

## 3. Newbie Autopilot vs Power User Mode

### 3.1 Newbie Autopilot

If you’re new or tired:

1. Drop the Toolkit into the chat.  
2. Provide your **report** or **source materials**.  
3. Say: **“Run this.”**  
4. Let it:
   - Spin up a **Story Spine**  
   - Propose next steps (usually writing code with the #2 prompt)  
5. When you don’t know what to say, just reply:  
   - **“Next.”**  
   - or **“Keep going.”**  
   - or **“Ok, now do the next logical step.”**

The System Context is designed to let the model steer reasonably.

---

### 3.2 Power User Mode (Once You Get It)

When you’re comfortable, you can call tools explicitly:

- “Run **Story Spine Builder** on this report.”  
- “Now run **Infographic Forge** using that Spine.”  
- “Re-theme it with **Themer** using this vibe: drummer-jazzy, midnight-club, muted neons.”  
- “Use **Hooksmith** to generate hooks + microcopy for X and LinkedIn.”  
- “Add subtle toys with **Toysmith** (medium intensity, analytical feel).”  
- “Run **Diagnostic Reviewer** on the final HTML and give me a punch list.”  
- “Platformize this for X + TikTok.”  
- “Turn it into a 10-slide LinkedIn carousel with **Carouselizer**.”

You can chain tools in one message:

> “Take the Deep Research above, run Story Spine, Forge, then Themer with a sober institutional theme. Show me the HTML.”

…but for clarity and debugging, it’s often nicer to do one major tool at a time. *(Plus you get to spend a whole turn's compute on just the one problem. Hooks and Viralizer go great together, though. --stun)*

---

## 4. Quick-Start: “Just Make Me a Good Infographic”

This is the **normal** workflow for most users.

### Step 0 – Get your source

You need something with **actual content**:

- Gemini Deep Research output  
- ChatGPT Inquiry Engine report  
- A structured brief / doc / outline  
- A nice collection of cleaned data in a csv
- A long-form blog post or essay  

Drop it into the chat or connect it to the chat with a connector like "Add from my Google Drive" (or make sure it’s already there in context).

---

### Step 1 – Load the Toolkit

1. Upload / paste `Infographic Prompts v1.x.md`.  
2. Say: **“Run this on attached report/materials/blog post/etc.”**

The model should:

- Recognize the Toolkit  
- Either explain the tools **or** go straight to **Story Spine Builder**

If it explains the tools and pauses, you can say:

> “Start with Story Spine Builder on my report.”

---

### Step 2 – Let Story Spine Builder do its job

You’ll get:

- A clear orientation (core idea / turn / payoff)  
- A 5–9 beat **spine**  
- A mapping of beats → panels  
- Variants (tight / lyrical / executive)

If you like it:  
> “Great. Now use Infographic Forge to build a full HTML page from this spine.”

If you don’t:  
> “Tighten this spine for an executive audience.”  
> “Add more tension around [X].”  
> “Reduce to 5 beats, keep only the strongest.”

---

### Step 3 – Run Infographic Forge

Prompt suggestion:

> “Use Infographic Forge. Treat the Story Spine you just created as the narrative skeleton. Output a complete HTML page in one code block. Assume placeholder data is OK.”

*(Or just say "Next." --stun)*

If you already know the title / tagline and plan to host it, you can add:

- `page_title` – short, strong title  
- `social_tagline` – 1–2 sentence description  

Example:

> “Run Infographic Forge with  
>  `page_title = The Silent Engine – Patreon Monetization Synthesis`,  
>  `social_tagline = A visual walk-through of how Patreon creators quietly build durable recurring revenue systems.`,  
>  placeholder data allowed.”

Later, when you’ve run **Hooksmith**, you can reuse its best 1–2 sentence description as the `social_tagline` for Forge (and for OG/Twitter meta descriptions).

Forge will:

- Produce a **mobile-first Tailwind HTML page**  
- Include optional Chart.js  
- Add **Open Graph + Twitter meta tags** if you provided metadata  
- Add TODO placeholders for URLs if you didn’t

---

### Step 4 – Optional: Run Themer

If Forge output looks structurally good but visually generic:

> “Run Themer on this infographic. Theme: [describe your vibe].”

Examples:

- “Institutional, muted, serious, no neon.”  
- “Urban fantasy with cool teals and brass highlights.”  

or, heck, this is an LLM not a computer and understands a paragraph, a poem, or even:

# THEME – FORGE PRAXIS
```
🎨 NAME: Forge Praxis

🌈 COLOR PALETTE:
Base: #2B2A28   (carbon basalt)
Primary: #A1A09A (titanium gray)
Highlight: #E6A34B (anodized amber)
Accent: #578C89   (oxidized teal)
Text: #ECE9E3     (ivory steel)

🧠 MOOD: Rational gravitas, precision under moral constraint, quiet creation
❤️ EMOTION: Focused integrity, reverence for craft, confidence born of calibration
🔤 FONT PREFERENCE: Headings — Space Grotesk or Eurostile Extended; Body — IBM Plex Mono or Inter
🔍 VISUAL MOTIF: Schematics etched into alloy, concentric tolerance rings, faint runes of formulae in margin light
💬 VIBE TAGS: "axiomatic engineering", "constraint dialogue", "systemic grace", "ethic-of-precision"
🌀 ANIMATED EFFECTS: Slow copper pulse along divider lines; brief highlight glint when equations resolve; telemetry dots oscillate near active variables
📦 USE CASE: Persona-engineering frameworks, design-method manifests, systems-thinking dashboards, metacog protocol docs
```

Themer will:

- Extract the vibe  
- Define a **palette system**  
- Define typography and micro-aesthetics  
- Emit code (Tailwind/CSS/Chart.js tweaks) you can apply on top of Forge

You can ask it to **apply the changes directly** or give you a patch to merge.

---

### Step 5 – Optional: Run Hooksmith & Viralizer

Once the visuals are decent, fix the **language and performance**.

**Hooksmith** focuses on:

- Hooks  
- Microcopy  
- Platform-specific snippets  
- LLM-friendly “fact cells”

**Viralizer** focuses on:

- Resequencing for scannability & flow  
- Virality signature (emotional + social vectors)  
- Platform-aware hooks & CTAs  
- SXO–GEO structure (alt text, fact cells, headings)  
- Code-level clarity tweaks

Examples:

> “Use Hooksmith on this infographic’s text. Give me hooks for X, LinkedIn, and IG, plus improved headings and captions.”

> “Run the hooks and viralize this.”

**Hand-off tip:**  
When Hooksmith gives you a standout 1–2 sentence description, that’s your `social_tagline` for:

- Forge’s `<meta name="description">`  
- `og:description`  
- `twitter:description`

---

### Step 6 – Optional: Add Toys with Toysmith

When you have a solid static infographic:

> “Run Toysmith with medium intensity, analytical vibe. The goal is subtle interactivity that deepens understanding without being flashy.”

Toysmith will:

- Propose a **Toy Map** (sliders, reveals, toggles, etc.)  
- Emit HTML/CSS/JS changes  
- Respect mobile and accessibility

If you’re nervous, you can say:

> “Toysmith: plan only, no code yet.”
*(I usually just say "add toys." and let it go ham. --stun)*

Then ask it to generate the code once you like the plan.

---

### Step 7 – Optional: Platformizer & Carouselizer

If you specifically want:

- An **IG / LinkedIn carousel**  
- A **TikTok / Reels script**  
- A **native-feeling X thread**  
- A **LinkedIn doc or Pinterest graphic flow**

Use:

- **Carouselizer** when the output is “a 6–14 card swipe thing.”  
- **Platformizer** when the output is “X thread + LinkedIn post + TikTok script, all from the same idea.”

Examples:

> “Use Carouselizer on this infographic for a 10-slide LinkedIn carousel, sober professional tone.”

> “Platformizer: adapt this core idea for X and TikTok. I want hooks, thread structure, and a short script.”

Think of it this way:

- **Viralizer** = “make this specific artifact work better everywhere.”  
- **Platformizer** = “rebuild the same idea in different *native* formats.”  
- **Carouselizer** = “turn this into a swipe sequence.”

---

### Step 8 – Optional: Diagnostic Reviewer

At any point (especially if you’re working off Gemini’s auto-infographic or something you already built):

> “Run Diagnostic Reviewer on this HTML and give me the top 3 fixes plus secondary improvements.”

Use it:

- Before investing in Themer/Toysmith  
- As a final QA pass before publishing  
- To rescue someone else’s messy artifact

---

## 5. Example Pipelines (Recipes)

### Recipe A – Deep Research → Web Infographic → Carousels

1. Run **Deep Research** (Gemini / Inquiry Engine / etc.).  
2. Load Toolkit → “Run this on the research above.”  
3. Accept / tweak **Story Spine**.  
4. Run **Infographic Forge** → get full HTML.  
5. Run **Themer** if you care about brand style.  
6. Run **Hooksmith** for hooks + microcopy.  
7. Run **Carouselizer** on the content for IG / LinkedIn carousels.  
8. Publish HTML to GitHub Pages (see next section).

---

### Recipe B – Fix GEMINI Auto-Infographic

1. In Gemini, hit **Create Infographic** on your content.  
2. Copy the resulting HTML / description.  
3. Load Toolkit in a new chat.  
4. “Use the Infographic Toolkit from the file above. Run Diagnostic Reviewer on this infographic.”  
5. Apply top 3 fixes manually, or:  
   - “Use Forge to rebuild this infographic with the same idea but better structure.”  
   - “Run Themer to restyle it according to [vibe].”  
   - “Use Toysmith for light interactivity.”  
   - “Use Viralizer for better performance and SXO–GEO.”

---

### Recipe C – “Just Give Me a Strong IG Carousel”

1. Load Toolkit + your report / idea.  
2. “Run Story Spine Builder on this.”  
3. “Now use Carouselizer to build a 9–10 slide IG carousel.”  
4. Optionally: “Use Hooksmith to refine the slide text and hooks.”

You can skip Forge entirely in this flow.

---

### Recipe D – “I Want a Good X Thread / LinkedIn Post”

1. Load Toolkit + source content.  
2. Optional: Story Spine Builder for clarity.  
3. “Use Platformizer to adapt this for X and LinkedIn. Tone: [describe].”  
4. Optionally: “Use Hooksmith to refine the thread/copy.”

---

## 6. Hosting Your Infographic on GitHub Pages (or *"Soooo... I have the code... Now what?"*)

You have a great `.html` asset you've probably already previewed by saving as a local file or loading in a Canvas, but what you need is a shareable URL with a nice embed. That means hosting. There're innumberable ways to go about this, but this is one of the simplest and best documented (ie. the model can probably help if you get stuck).

Use Github Pages.

You don’t need to know git. You can do all of this in the GitHub website UI.

### 6.1 Create a GitHub account (if needed)

1. Go to https://github.com  
2. Click **Sign up** and follow the steps.  
3. After setup, you’ll land on your dashboard.

---

### 6.2 Create a repository for infographics

1. Click the **+** icon (top right) → **New repository**.  
2. Name it something like `infographics` or `my-infographics`.  
3. Choose **Public**.  
4. Check the **Add a README file** box (optional but fine).  
5. Leave **.gitignore** and **License** as **None** unless you care.  
6. Click **Create repository**.

---

### 6.3 Turn on GitHub Pages

1. Inside your new repo, click the **Settings** tab.  
2. In the sidebar, click **Pages**.  
3. Under **Source**:
   - Choose **Deploy from a branch**.  
   - Set **Branch** to `main` (or whatever your default is).  
   - Set **Folder** to `/ (root)`.  
4. Click **Save**.

After a minute or so, your site will be live at:

`https://YOUR_USERNAME.github.io/REPO_NAME/`

---

### 6.4 Create a folder for one infographic

You’ll give each infographic its own folder with an `index.html`.

1. From the repo main page, click **Add file** → **Create new file**.  
2. For the filename, type something like:

   `infographic-title/index.html`

   - Use only lowercase, numbers, `-` or `_` (no spaces).  
   - That folder name becomes part of the URL.

(You'd think there'd be a "create folder" button, but no. You create a file in a new folder to make one.)

3. In the big editor box, paste the **HTML output from Infographic Forge and later tools**.  
4. Scroll down and click **Commit changes**.

Your infographic is now at:

`https://YOUR_USERNAME.github.io/REPO_NAME/infographic-title/`

---

### 6.5 Add a thumbnail image (1200×675 recommended)

Once you have the infographic displaying, create a thumbnail. (Winkey+S, a clip, then Paint/Paint3D will do it. Shoot for 16:9, 1200x675 for twixxer card embed-native.) Then upload it to your repo (in a sub-folder by convention).

1. From the repo main page, click **Add file** → **Upload files**.  
2. At the top of the upload page where it shows the path, type:

   `infographic-title/assets/`

3. Upload your `thumbnail.png` (or `.jpg`) into that folder.  
4. Click **Commit changes**.

The full thumbnail URL will look like:

`https://YOUR_USERNAME.github.io/REPO_NAME/infographic-title/assets/thumbnail.png`

---

### 6.6 Wire up the social metadata

Infographic Forge already knows how to **emit OG + Twitter meta tags** if you provide:

- `page_title`  
- `social_tagline`  
- `canonical_url`  
- `thumbnail_url`  
- (`twitter_handle` optional)

Most of the time, you **won’t know `canonical_url` or `thumbnail_url` yet** when you first run Forge.

So you have two options:

#### Option A – Let Forge create TODO placeholders

When you run Forge without URLs, it will emit something like:

```html
<!-- TODO: Replace with the final live URL of this infographic -->
<meta property="og:url" content="[[SET_FINAL_URL_HERE]]" />

<!-- TODO: Replace with the full URL to your 1200x675 thumbnail -->
<meta property="og:image" content="[[SET_THUMBNAIL_URL_HERE]]" />
````

After you’ve set up GitHub Pages and the thumbnail:

1. Go to `index.html` in GitHub.

2. Click the **pencil** (Edit).

3. Replace:

   * `[[SET_FINAL_URL_HERE]]` with:
     `https://YOUR_USERNAME.github.io/REPO_NAME/infographic-title/`

   * `[[SET_THUMBNAIL_URL_HERE]]` with:
     `https://YOUR_USERNAME.github.io/REPO_NAME/infographic-title/assets/thumbnail.png`

4. Update `og:title`, `og:description`, `twitter:title`, `twitter:description` if needed.

5. Click **Commit changes**.

Forge ensures the meta block is placed **after any `<style>` block and before `</head>`**, which is important for clean embeds.

---

#### Option B – Re-run Forge with final URLs

If you prefer to keep everything generated by the model:

1. Set up GitHub Pages and thumbnail first.
2. Note your final `canonical_url` and `thumbnail_url`.
3. Go back to the model and say:

> “Add this metadata like in the Infographic Forge:
> `page_title = ...`
> `social_tagline = ...`
> `canonical_url = https://...`
> `thumbnail_url = https://...`
> `twitter_handle = @...`.”

(it should use placeholders for any you don't have.)

4. Paste the updated HTML into `index.html` in GitHub.

Either way is fine. Option A is usually quicker in practice.

---

### 6.7 Test the page & previews

1. Visit your infographic URL in a browser.
2. For X/Twitter, use a Card Validator (twitter used to have one, but there are numerous such. I use a Chrome plugin.).
3. For LinkedIn, paste the URL into a new post and see what shows up after a moment.

If the title, description, and thumbnail look right, you’re good.

---

## 7. Model Quirks & Troubleshooting

### 7.1 The model just summarized my report instead of using the tools

Remind it:

> “You are running the Infographic Toolkit. Use the tools defined in the file, starting with Story Spine Builder. Do not give me a generic summary.”

If it still resists, be even more explicit:

> “Run **1. Story Spine Builder** exactly as written in the Toolkit file I provided. Follow its steps and output all specified sections.”

For Gemini specifically, this phrasing helps:

> “Use the Infographic Toolkit prompts from the file above as your instructions. Do not invent a new approach; follow that file.”

---

### 7.2 The HTML got truncated

* Ask the model to **re-send only the HTML** in one code block.
* If needed, say:

> “Only output the HTML for the infographic, in a single fenced code block. No commentary, no explanations.”

If it still chokes, you can add:

> “Reduce less important sections and keep the total length under [X] tokens, but keep the full code in one block.”

---

### 7.3 OG / Twitter preview isn’t updating

* Social platforms cache previews.
* Use their debugger tools (Twitter Card Validator, Facebook Sharing Debugger) to force a refresh.
* Make sure:

  * The URL in `og:url` matches the live page.
  * The URL in `og:image` / `twitter:image` is correct and public.
  * Thumbnail is a reasonable size (1200×675 is safe).

---

### 7.4 It’s too pretty / too busy

Ask for:

> “A flatter, calmer, more institutional theme, minimal color accents, no gradients.”

or 

> “Dial back the toys a bit. Maybe switch to a more professional theme.”

Ask the model to:

> “Optimize for clarity first, virality second. Reduce visual clutter and simplify hierarchy.”

---

## 8. Summary: How to Think About the Toolkit

* **Story Spine Builder** – make the idea narratable.
* **Infographic Forge** – make it a real web page.
* **Themer** – make it look like it belongs to your world.
* **Hooksmith** – make the words do their job.
* **Viralizer** – make a given artifact perform in feeds & LLMs.
* **Toysmith** – make it playful and interactive.
* **Platformizer** – adapt the idea to IG/X/LinkedIn/TikTok/Shorts/Pinterest.
* **Carouselizer** – slice it into swipe-able slides.
* **Diagnostic Reviewer** – tell you what’s wrong and what to fix first.

Start simple:

> “Here’s my research. Here’s the Toolkit. Run this.”

Then grow into:

> “Spine → Forge → Themer → Hooksmith/Viralizer → Toysmith → GitHub → Platformizer/Carouselizer.”

You drive as much or as little as you like. The system is meant to flex. And the model is smart enough to generally apply and adapt its tools as needed if it knows to look in the file.

– stunspot | ⟨🤩⨯📍⟩ & 💠‍🌐 Nova