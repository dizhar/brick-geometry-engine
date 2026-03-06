"""
Pre-defined metadata for the common LEGO parts needed in Phase A.

All parts are keyed by their canonical part_id string and also accessible
through typed constants.  LDraw part numbers are provided where applicable.

Brick naming convention:  "brick_{L}x{W}"   e.g. brick_2x4
Plate naming convention:  "plate_{L}x{W}"   e.g. plate_2x4

LDraw IDs reference: https://www.ldraw.org/parts/
"""

from __future__ import annotations

from typing import Dict

from .part_metadata import PartMetadata, make_brick, make_plate


# ---------------------------------------------------------------------------
# Standard bricks  (height = 24 LDU = 9.6 mm)
# ---------------------------------------------------------------------------

BRICK_1x1 = make_brick("brick_1x1", "Brick 1×1",  studs_x=1, studs_z=1, ldraw_id="3005")
BRICK_1x2 = make_brick("brick_1x2", "Brick 1×2",  studs_x=1, studs_z=2, ldraw_id="3004")
BRICK_1x3 = make_brick("brick_1x3", "Brick 1×3",  studs_x=1, studs_z=3, ldraw_id="3622")
BRICK_1x4 = make_brick("brick_1x4", "Brick 1×4",  studs_x=1, studs_z=4, ldraw_id="3010")
BRICK_1x6 = make_brick("brick_1x6", "Brick 1×6",  studs_x=1, studs_z=6, ldraw_id="3009")
BRICK_1x8 = make_brick("brick_1x8", "Brick 1×8",  studs_x=1, studs_z=8, ldraw_id="3008")
BRICK_2x2 = make_brick("brick_2x2", "Brick 2×2",  studs_x=2, studs_z=2, ldraw_id="3003")
BRICK_2x3 = make_brick("brick_2x3", "Brick 2×3",  studs_x=2, studs_z=3, ldraw_id="3002")
BRICK_2x4 = make_brick("brick_2x4", "Brick 2×4",  studs_x=2, studs_z=4, ldraw_id="3001")
BRICK_2x6 = make_brick("brick_2x6", "Brick 2×6",  studs_x=2, studs_z=6, ldraw_id="2456")
BRICK_2x8 = make_brick("brick_2x8", "Brick 2×8",  studs_x=2, studs_z=8, ldraw_id="3007")
BRICK_2x10 = make_brick("brick_2x10","Brick 2×10", studs_x=2, studs_z=10, ldraw_id="3006")
BRICK_4x4 = make_brick("brick_4x4", "Brick 4×4",  studs_x=4, studs_z=4, ldraw_id="2344")
BRICK_4x6 = make_brick("brick_4x6", "Brick 4×6",  studs_x=4, studs_z=6, ldraw_id="2356")

# ---------------------------------------------------------------------------
# Standard plates  (height = 8 LDU = 3.2 mm)
# ---------------------------------------------------------------------------

PLATE_1x1  = make_plate("plate_1x1",  "Plate 1×1",  studs_x=1, studs_z=1,  ldraw_id="3024")
PLATE_1x2  = make_plate("plate_1x2",  "Plate 1×2",  studs_x=1, studs_z=2,  ldraw_id="3023")
PLATE_1x3  = make_plate("plate_1x3",  "Plate 1×3",  studs_x=1, studs_z=3,  ldraw_id="3623")
PLATE_1x4  = make_plate("plate_1x4",  "Plate 1×4",  studs_x=1, studs_z=4,  ldraw_id="3710")
PLATE_1x6  = make_plate("plate_1x6",  "Plate 1×6",  studs_x=1, studs_z=6,  ldraw_id="3666")
PLATE_1x8  = make_plate("plate_1x8",  "Plate 1×8",  studs_x=1, studs_z=8,  ldraw_id="3460")
PLATE_2x2  = make_plate("plate_2x2",  "Plate 2×2",  studs_x=2, studs_z=2,  ldraw_id="3022")
PLATE_2x3  = make_plate("plate_2x3",  "Plate 2×3",  studs_x=2, studs_z=3,  ldraw_id="3021")
PLATE_2x4  = make_plate("plate_2x4",  "Plate 2×4",  studs_x=2, studs_z=4,  ldraw_id="3020")
PLATE_2x6  = make_plate("plate_2x6",  "Plate 2×6",  studs_x=2, studs_z=6,  ldraw_id="3795")
PLATE_2x8  = make_plate("plate_2x8",  "Plate 2×8",  studs_x=2, studs_z=8,  ldraw_id="3034")
PLATE_2x10 = make_plate("plate_2x10", "Plate 2×10", studs_x=2, studs_z=10, ldraw_id="3832")
PLATE_4x4  = make_plate("plate_4x4",  "Plate 4×4",  studs_x=4, studs_z=4,  ldraw_id="3031")
PLATE_4x6  = make_plate("plate_4x6",  "Plate 4×6",  studs_x=4, studs_z=6,  ldraw_id="3032")
PLATE_4x8  = make_plate("plate_4x8",  "Plate 4×8",  studs_x=4, studs_z=8,  ldraw_id="3035")
PLATE_6x6  = make_plate("plate_6x6",  "Plate 6×6",  studs_x=6, studs_z=6,  ldraw_id="3958")
PLATE_6x8  = make_plate("plate_6x8",  "Plate 6×8",  studs_x=6, studs_z=8,  ldraw_id="3036")
PLATE_6x10 = make_plate("plate_6x10", "Plate 6×10", studs_x=6, studs_z=10, ldraw_id="3033")
PLATE_8x8  = make_plate("plate_8x8",  "Plate 8×8",  studs_x=8, studs_z=8,  ldraw_id="41539")

# ---------------------------------------------------------------------------
# Lookup registry
# ---------------------------------------------------------------------------

#: All Phase-A parts keyed by part_id.
ALL_PARTS: Dict[str, PartMetadata] = {
    p.part_id: p
    for p in [
        # bricks
        BRICK_1x1, BRICK_1x2, BRICK_1x3, BRICK_1x4,
        BRICK_1x6, BRICK_1x8,
        BRICK_2x2, BRICK_2x3, BRICK_2x4, BRICK_2x6,
        BRICK_2x8, BRICK_2x10,
        BRICK_4x4, BRICK_4x6,
        # plates
        PLATE_1x1, PLATE_1x2, PLATE_1x3, PLATE_1x4,
        PLATE_1x6, PLATE_1x8,
        PLATE_2x2, PLATE_2x3, PLATE_2x4, PLATE_2x6,
        PLATE_2x8, PLATE_2x10,
        PLATE_4x4, PLATE_4x6, PLATE_4x8,
        PLATE_6x6, PLATE_6x8, PLATE_6x10,
        PLATE_8x8,
    ]
}

#: Convenience sub-registries.
BRICKS: Dict[str, PartMetadata] = {k: v for k, v in ALL_PARTS.items() if k.startswith("brick_")}
PLATES: Dict[str, PartMetadata] = {k: v for k, v in ALL_PARTS.items() if k.startswith("plate_")}


def get_part(part_id: str) -> PartMetadata:
    """Return the PartMetadata for *part_id*, raising KeyError if unknown."""
    try:
        return ALL_PARTS[part_id]
    except KeyError:
        raise KeyError(f"Unknown part_id {part_id!r}. Available: {sorted(ALL_PARTS)}")


def get_parts_by_footprint(studs_x: int, studs_z: int) -> list[PartMetadata]:
    """Return all parts whose stud footprint matches (studs_x × studs_z)."""
    return [
        p for p in ALL_PARTS.values()
        if p.dimensions.studs_x == studs_x and p.dimensions.studs_z == studs_z
    ]


def get_parts_by_ldraw_id(ldraw_id: str) -> PartMetadata | None:
    """Return the part with the given LDraw number, or None if not found."""
    for p in ALL_PARTS.values():
        if p.ldraw_id == ldraw_id:
            return p
    return None
