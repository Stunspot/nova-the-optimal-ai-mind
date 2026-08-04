# Boundaries are where classifications change

Partition inputs by behavior, not by surface type. An equivalence class contains values expected to receive the same treatment; a boundary is where that treatment changes.

Probe each meaningful threshold with `below / at / above`, plus absence, malformed form, and extreme scale where applicable. Include semantic boundaries: tenant ownership, role, state, timezone, precision, normalization, encoding, empty versus missing, duplicate versus new, expired versus active.

Representative values earn coverage only when the class definition is justified. “One valid and one invalid” is too coarse when validity contains materially different parsing, authorization, or persistence paths.

Preserve contract distinctions such as `null`, missing field, empty string, zero, and default only when the target system treats them differently. Do not create combinatorial volume without a risk-bearing interaction.
