"""
Pre-defined metadata for common LEGO slope parts (Phase B).

Slope geometry convention
-------------------------
The slope rises from *height_low_ldu* at z = 0 (the low / front end) to
*height_high_ldu* at z = depth (the high / back end).  In the LEGO system,
the high end is always at least one plate high (8 LDU) and the highest
point equals one brick height (24 LDU) for the standard range below.

LDraw reference IDs are provided where applicable.

Naming convention:  "slope_{studs_x}x{studs_z}_{description}"
"""

from __future__ import annotations

from typing import Dict

from .part_metadata import PartMetadata, make_slope
from ..core.constants import PLATE_HEIGHT_LDU, BRICK_HEIGHT_LDU

# Convenient height aliases
_P = float(PLATE_HEIGHT_LDU)   # 8 LDU
_B = float(BRICK_HEIGHT_LDU)   # 24 LDU
_2P = 2 * _P                   # 16 LDU (2 plates)

# ---------------------------------------------------------------------------
# 1×1 slopes  (steep)
# ---------------------------------------------------------------------------

# 1×1 Slope 75° — rises from 0 (floor) to 1 brick over 1 stud.
# LDraw 54200; no flat top stud, so flat_rows_at_high_end=0.
SLOPE_1x1_STEEP = make_slope(
    "slope_1x1_steep",  "Slope 1×1 Steep",
    studs_x=1, studs_z=1,
    height_low_ldu=0.0, height_high_ldu=_B,
    flat_rows_at_high_end=0,
    ldraw_id="54200",
)

# ---------------------------------------------------------------------------
# 1×2 slopes
# ---------------------------------------------------------------------------

# 1×2 Slope 45° — rises from 0 to 1 brick over 2 studs.
# LDraw 3040b; has 1 stud at the high (back) end.
SLOPE_1x2_45 = make_slope(
    "slope_1x2_45", "Slope 1×2 45°",
    studs_x=1, studs_z=2,
    height_low_ldu=0.0, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3040b",
)

# 1×2 Slope 30° (gentle) — rises from 1 plate to 1 brick over 2 studs.
# LDraw 3040a.
SLOPE_1x2_30 = make_slope(
    "slope_1x2_30", "Slope 1×2 30°",
    studs_x=1, studs_z=2,
    height_low_ldu=_P, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3040a",
)

# 1×2 Inverted Slope 45° — the underside of a 45° slope (same heights, but
# used as an inverted wedge; anti-studs on top, studs on bottom).
# LDraw 3665.  For Phase B we model it identically to the standard slope;
# the "inverted" semantic affects only visual geometry (out of scope).
SLOPE_1x2_INV = make_slope(
    "slope_1x2_inv", "Slope 1×2 Inverted",
    studs_x=1, studs_z=2,
    height_low_ldu=_P, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3665",
)

# ---------------------------------------------------------------------------
# 2×2 slopes
# ---------------------------------------------------------------------------

# 2×2 Slope 45° — rises from 0 to 1 brick over 2 studs (Z axis).
# LDraw 3039; has 1 row of 2 studs at the high end.
SLOPE_2x2_45 = make_slope(
    "slope_2x2_45", "Slope 2×2 45°",
    studs_x=2, studs_z=2,
    height_low_ldu=0.0, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3039",
)

# 2×2 Slope 30° — rises from 1 plate to 1 brick over 2 studs.
# LDraw 3038.
SLOPE_2x2_30 = make_slope(
    "slope_2x2_30", "Slope 2×2 30°",
    studs_x=2, studs_z=2,
    height_low_ldu=_P, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3038",
)

# 2×2 Inverted Slope 45°.  LDraw 3660.
SLOPE_2x2_INV = make_slope(
    "slope_2x2_inv", "Slope 2×2 Inverted",
    studs_x=2, studs_z=2,
    height_low_ldu=_P, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3660",
)

# ---------------------------------------------------------------------------
# 2×3 slopes
# ---------------------------------------------------------------------------

# 2×3 Slope 25° — rises from 1 plate to 1 brick over 3 studs.
# LDraw 3298; has 1 row of 2 studs at the high end.
SLOPE_2x3_25 = make_slope(
    "slope_2x3_25", "Slope 2×3 25°",
    studs_x=2, studs_z=3,
    height_low_ldu=_P, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3298",
)

# ---------------------------------------------------------------------------
# 2×4 slopes
# ---------------------------------------------------------------------------

# 2×4 Slope 45° — rises from 0 to 1 brick over 4 studs.
# LDraw 3037.
SLOPE_2x4_45 = make_slope(
    "slope_2x4_45", "Slope 2×4 45°",
    studs_x=2, studs_z=4,
    height_low_ldu=0.0, height_high_ldu=_B,
    flat_rows_at_high_end=1,
    ldraw_id="3037",
)

# 2×4 Slope 18° — rises from 2 plates to 1 brick over 4 studs (gentle).
# LDraw 3036.
SLOPE_2x4_18 = make_slope(
    "slope_2x4_18", "Slope 2×4 18°",
    studs_x=2, studs_z=4,
    height_low_ldu=_2P, height_high_ldu=_B,
    flat_rows_at_high_end=2,
    ldraw_id="3036",
)

# ---------------------------------------------------------------------------
# Lookup registry
# ---------------------------------------------------------------------------

ALL_SLOPES: Dict[str, PartMetadata] = {
    p.part_id: p
    for p in [
        SLOPE_1x1_STEEP,
        SLOPE_1x2_45, SLOPE_1x2_30, SLOPE_1x2_INV,
        SLOPE_2x2_45, SLOPE_2x2_30, SLOPE_2x2_INV,
        SLOPE_2x3_25,
        SLOPE_2x4_45, SLOPE_2x4_18,
    ]
}


def get_slope(part_id: str) -> PartMetadata:
    """Return the PartMetadata for *part_id*, raising KeyError if unknown."""
    try:
        return ALL_SLOPES[part_id]
    except KeyError:
        raise KeyError(
            f"Unknown slope part_id {part_id!r}. "
            f"Available: {sorted(ALL_SLOPES)}"
        )
