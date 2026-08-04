# Make the workbook inspectable before making it impressive

A spreadsheet is a compact model of a working reality. Start with what a number means, where it came from, and who will update it; then shape sheets, formulas, and visuals so a reader can inspect the result without reverse-engineering it.

## Establish the data model

Define each sheet's role: source data, assumptions, calculation, analysis, or presentation. Give columns one meaning, units one home, and dates an explicit grain. Keep raw imported data distinct from transformed calculations. Name assumptions, calculation boundaries, and refresh expectations where they affect a decision.

Preserve formulas for values intended to recalculate. A displayed total that hides its logic is a presentation artifact, not an auditable workbook. Where a source value is manually supplied, label its status instead of giving it formula-like authority.

## Use formulas with visible lineage

Build calculations from clear references, make denominators and time periods legible, and prevent silent mixing of units, currencies, or scopes. Recalculate or inspect formulas using the capability available; scan for error cells, broken references, inconsistent formulas in a range, unexpected hard-coded values, and totals that do not reconcile with their components.

When a formula cannot be evaluated in the active host, preserve the formula text and input lineage, label calculation verification as unperformed, and avoid presenting the result as checked arithmetic.

## Design for scanning and use

Use a small number of purposeful sheets. Provide an orienting first sheet or summary when the workbook serves a decision. Make headings distinct, freeze or repeat context where the environment supports it, format numbers according to their units, and keep input, calculated, and final-value cells visually distinguishable without turning the workbook into a color code puzzle.

Choose charts only when a visual comparison clarifies the reader's question. Give every chart a title that states the comparison, readable labels, an honest scale, visible units, and a source relationship. A chart that obscures a denominator or time range adds confidence theater rather than insight.

## Audit before handoff

Inspect data ranges, sheet names, formula coverage, totals, defined assumptions, filters or tables where appropriate, charts, links, hidden rows/columns, and visible error states. Review the workbook's reading order and visual density in an available native or rendered view. Treat macros, external connections, protected content, and live-data relationships as explicit boundaries; leave them inactive unless the user authorizes a compatible route.

Record the workbook as editable, recalculable, structurally inspected, visually inspected, or pending a native recalculation according to what actually occurred. Feed any metrics used in documents, decks, or PDFs back through the content ledger so later derivatives retain the same figures and units.
