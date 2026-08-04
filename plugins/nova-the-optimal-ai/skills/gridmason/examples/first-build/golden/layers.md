# First Build

Artifact: `first-build`
Coordinate frame: x east-positive; y up-positive; z south-positive; origin is the minimum corner.
Air policy: omitted cells are air.

## Palette

| Key | Block ID | States | Count |
| --- | --- | --- | ---: |
| GLASS | `minecraft:glass` | `{}` | 2 |
| OAK | `minecraft:oak_planks` | `{}` | 4 |
| STONE | `minecraft:cobblestone` | `{}` | 12 |

## Layer y=0

`z \ x` | 0 | 1 | 2 | 3
--- | --- | --- | --- | ---
0 | STONE | STONE | STONE | STONE
1 | STONE | . | . | STONE
2 | STONE | . | . | STONE
3 | STONE | STONE | STONE | STONE

## Layer y=1

`z \ x` | 0 | 1 | 2 | 3
--- | --- | --- | --- | ---
0 | OAK | GLASS | GLASS | OAK
1 | . | . | . | .
2 | . | . | . | .
3 | OAK | . | . | OAK
