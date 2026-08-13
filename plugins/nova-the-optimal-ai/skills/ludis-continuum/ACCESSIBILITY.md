# Accessibility

Ludis Continuum documentation is designed for keyboard access, readable reflow, reduced motion, descriptive links, and explicit separation between player-safe and GM-only information.

## Documentation commitments

- One top-level heading per page with a logical heading hierarchy.
- A skip link and landmark structure on the Pages site.
- Visible keyboard focus that is not conveyed by color alone.
- Text alternatives that describe an image's product meaning rather than decorative detail.
- No essential text embedded only in README or Pages hero art.
- Social-card text is duplicated in page metadata and nearby HTML.
- Tables are used only for genuine relationships and remain readable on narrow screens.
- Code samples are copyable text, not images.
- Generated map and token examples carry purpose-based alt text in the ledger and explanatory prose nearby.
- Player approval previews use a declared language, logical headings, labeled tables, visible borders, and wrap long hashes. The preview remains partial; approval also requires review of every candidate member, including listening to audio, inspecting other non-rendered formats, and treating code as text without executing it.
- There is no animated content; smooth anchor scrolling is disabled under `prefers-reduced-motion`.
- Color is paired with labels for status and visibility.

## Product-use boundary

Ludis can help a creator plan accessible handouts or ask about player preferences, but it cannot certify an adventure, game system, VTT, image, PDF, or live session as accessible. Generated material still needs review with the people who will use it.

Consent, disability, and accommodation information can be sensitive. Record only what participants choose to share, separate operational needs from unnecessary personal detail, and follow [SECURITY.md](SECURITY.md).

## Known limits

- The repository does not include bundled audio, captions, transcripts, tactile maps, or a VTT interface. Exported metadata cannot make a target VTT accessible by itself.
- Markdown rendering and skill invocation UI belong to the host and may vary.
- Hero artwork is supplementary; it is not intended to communicate instructions.
- Automated contrast and markup checks do not replace keyboard, zoom, screen-reader, or cognitive walkthroughs.

## Report an accessibility defect

Open a [GitHub issue](https://github.com/Stunspot/ludis-continuum/issues) with the page, browser or host, assistive technology if relevant, expected behavior, and observed barrier. Do not include private player or campaign information.