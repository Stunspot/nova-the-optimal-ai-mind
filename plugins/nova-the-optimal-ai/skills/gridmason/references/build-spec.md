# Gridmason Build Spec v1

The Build Spec is the package’s neutral, deterministic design contract. It is not a Minecraft native file and does not prove in-game compatibility.

Use a Build Spec only when the player has approved a footprint and the placements are formal rather than inferred from a single screenshot.

If the player supplied an inventory or material budget, reconcile every required block or functional component against it. Mark unlisted supplies explicitly and offer a listed-material substitution or later stage; static coordinate precision does not excuse an impossible shopping list.

## Coordinate convention

Placements use integer coordinates relative to the declared origin:

- `x`: east-positive;
- `y`: up-positive;
- `z`: south-positive.

`size.x`, `size.y`, and `size.z` define an exclusive upper bound starting at zero. A placement at `(0,0,0)` is the minimum corner; `(size.x - 1, size.y - 1, size.z - 1)` is the maximum.

## Palette

Each palette entry is an object with:

- `key`: a short uppercase identifier used by placements;
- `block_id`: a namespaced block identifier such as `minecraft:stone`;
- `states`: an explicit property-to-value map, empty when no state is required;
- `swatch`: an uppercase six-digit color used only by the schematic preview.

The compiler sorts keys and state properties during canonicalization. It checks shape, references, and internal consistency only; it does not establish that a block or state exists in the target game version. Use `minecraft:` for vanilla IDs only when the player or a current source establishes the ID.

## Unsupported in v1

Entities, block entities and their data, scheduled ticks, inventories, biomes, fluids as world simulation, random ticks, commands, functions, native file metadata, automatic rotation, and game rendering remain unsupported. Record any required feature in `unsupported`; do not hide it in prose.

## Compiler result

`scripts/gridmason_build.py compile SPEC --out DIR` writes:

- `build-spec.canonical.json`
- `build-spec.sha256`
- `materials.csv`
- `layers.md`
- `preview.svg`
- `compile-receipt.json`

The receipt may state `STATICALLY VALID`. It must never state that the build loads, renders, functions, or was placed in Minecraft.

Run `validate SPEC` when only validation is needed. Run `canonicalize SPEC --output FILE` to produce canonical JSON without derivatives.
