"""
Pre-defined metadata for common LEGO Technic parts (Phase B).

All Technic bricks in this module have the same height as a standard brick
(24 LDU = BRICK_HEIGHT_LDU) and carry regular top studs plus Technic axle
holes along the X axis at every stud position.

Naming conventions
------------------
Technic Bricks:  "technic_brick_{L}x{W}"  (same footprint language as bricks)
Technic Beams:   "technic_beam_1x{N}"      (liftarms — same height, no studs
                                             on top; Phase C scope; stubbed here
                                             as standard Technic bricks for now)

LDraw reference IDs are provided where applicable.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .part_metadata import PartMetadata, make_technic_brick


# ---------------------------------------------------------------------------
# 1×N Technic Bricks  (studs on top, anti-studs on bottom, holes along X)
# ---------------------------------------------------------------------------

TECHNIC_BRICK_1x1 = make_technic_brick(
    "technic_brick_1x1", "Technic Brick 1×1 with Hole",
    studs_x=1, studs_z=1,
    hole_axis="x",
    ldraw_id="6541",
)

TECHNIC_BRICK_1x2 = make_technic_brick(
    "technic_brick_1x2", "Technic Brick 1×2 with Holes",
    studs_x=1, studs_z=2,
    hole_axis="x",
    ldraw_id="3700",
)

TECHNIC_BRICK_1x4 = make_technic_brick(
    "technic_brick_1x4", "Technic Brick 1×4 with Holes",
    studs_x=1, studs_z=4,
    hole_axis="x",
    ldraw_id="3701",
)

TECHNIC_BRICK_1x6 = make_technic_brick(
    "technic_brick_1x6", "Technic Brick 1×6 with Holes",
    studs_x=1, studs_z=6,
    hole_axis="x",
    ldraw_id="3894",
)

TECHNIC_BRICK_1x8 = make_technic_brick(
    "technic_brick_1x8", "Technic Brick 1×8 with Holes",
    studs_x=1, studs_z=8,
    hole_axis="x",
    ldraw_id="3702",
)

TECHNIC_BRICK_1x10 = make_technic_brick(
    "technic_brick_1x10", "Technic Brick 1×10 with Holes",
    studs_x=1, studs_z=10,
    hole_axis="x",
    ldraw_id="2730",
)

TECHNIC_BRICK_1x12 = make_technic_brick(
    "technic_brick_1x12", "Technic Brick 1×12 with Holes",
    studs_x=1, studs_z=12,
    hole_axis="x",
    ldraw_id="3895",
)

# ---------------------------------------------------------------------------
# 2×N Technic Bricks
# ---------------------------------------------------------------------------

TECHNIC_BRICK_2x2 = make_technic_brick(
    "technic_brick_2x2", "Technic Brick 2×2 with Holes",
    studs_x=2, studs_z=2,
    hole_axis="x",
    ldraw_id="32000",
)

TECHNIC_BRICK_2x4 = make_technic_brick(
    "technic_brick_2x4", "Technic Brick 2×4 with Holes",
    studs_x=2, studs_z=4,
    hole_axis="x",
    ldraw_id="32199",
)

# ---------------------------------------------------------------------------
# Lookup registry
# ---------------------------------------------------------------------------

ALL_TECHNIC: Dict[str, PartMetadata] = {
    p.part_id: p
    for p in [
        TECHNIC_BRICK_1x1,
        TECHNIC_BRICK_1x2,
        TECHNIC_BRICK_1x4,
        TECHNIC_BRICK_1x6,
        TECHNIC_BRICK_1x8,
        TECHNIC_BRICK_1x10,
        TECHNIC_BRICK_1x12,
        TECHNIC_BRICK_2x2,
        TECHNIC_BRICK_2x4,
    ]
}


def get_technic_part(part_id: str) -> PartMetadata:
    """Return the PartMetadata for *part_id*, raising KeyError if unknown."""
    try:
        return ALL_TECHNIC[part_id]
    except KeyError:
        raise KeyError(
            f"Unknown Technic part_id {part_id!r}. "
            f"Available: {sorted(ALL_TECHNIC)}"
        )
