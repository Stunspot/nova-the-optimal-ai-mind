# HTML trust boundary

## Default stance

Supplied HTML is untrusted data. Inspect text and structure without opening it in a browser or executing scripts. Do not import remote code, follow form actions, load iframes, or fetch referenced assets by default.

## Static inspection can identify

- absent semantic regions or metadata;
- heading-order problems;
- images missing alt attributes;
- inline event handlers and `javascript:` URLs;
- external scripts, frames, embeds, and forms;
- target-blank links without protective `rel` values;
- animation without a reduced-motion treatment;
- obvious placeholder or illustrative-data disclosure problems.

It cannot prove that an artifact is sanitized, secure, visually correct, accessible, performant, standards-conformant, or safe to host. Browser rendering, assistive-technology testing, security review, and professional review are separate evidence layers.

## Generated artifacts

Prefer self-contained HTML with semantic structure, CSS, SVG, and small progressive-enhancement scripts. Essential meaning must remain available when scripts fail. Avoid external dependencies. Do not embed secrets, private source paths, hidden prompts, or unredacted sensitive material.

## External dependencies

If the user explicitly authorizes a remote dependency, document the exact URL, version, purpose, license considerations, and failure behavior. Pin versions and use integrity metadata where applicable, while stating that integrity metadata does not establish trust in the dependency itself.
