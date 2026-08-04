# Documentation accessibility

The Beryl IT Benchcraft documentation is authored to support keyboard, screen-reader, magnification, mobile, and cognitively varied reading paths in plain Markdown-compatible renderers.

## Authored accessibility features

- One descriptive page title and logical heading order per topic.
- Real lists and simple tables used only for relationships.
- Meaningful link text that predicts the destination.
- Literal control and skill names rather than color, position, or shape alone.
- Actions followed by observable results and recovery branches.
- Warnings placed before the hazardous action.
- Short sections, familiar terms, progressive disclosure, and consistent vocabulary.
- Code examples duplicated in surrounding prose where their purpose matters.
- No customer instruction depends on the Beryl image.

## Review basis

Markdown structure is reviewed against the package’s documentation rules and the Hesperos accessible-documentation method. WCAG 2.2 principles inform web-oriented structure, and WCAG2ICT principles inform non-web interpretation where applicable.

This is not a formal WCAG conformance claim. Markdown rendering, theme contrast, focus behavior, link presentation, code-block scrolling, and announced table semantics depend on the host that displays the files.

## Untested paths

The v0.1.0 documentation build did not include representative-user testing, browser rendering across multiple engines, keyboard-only walkthrough in a published site, screen-reader testing, magnification testing, localization, or formal accessibility assessment.

Automated Markdown lint and manual semantic review can find selected structural and cognitive defects. They cannot establish usability or conformance.

## Report a documentation barrier

When reporting a barrier, include:

- document title and release version;
- heading or link text where the problem occurs;
- renderer or host and version;
- browser and assistive technology, if relevant;
- expected and observed behavior;
- whether the problem blocks finding, understanding, acting, or recovering.

Send the report through the release owner’s established feedback channel. This package does not define or operate an external support endpoint.
