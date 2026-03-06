"""
Coordinate system utilities for the LEGO geometry engine.

All internal positions are stored in LDU (LEGO Drawing Units).
  - X: right
  - Y: up   (positive Y points upward, matching LDraw convention)
  - Z: toward viewer

Conversion helpers and grid-snapping functions are provided so that
callers can work in whichever unit is most convenient.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from .constants import (
    LDU_TO_MM,
    MM_TO_LDU,
    STUD_SPACING_LDU,
    PLATE_HEIGHT_LDU,
    BRICK_HEIGHT_LDU,
    POSITION_TOLERANCE_LDU,
)


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

def ldu_to_mm(value: float) -> float:
    """Convert LDU to millimetres."""
    return value * LDU_TO_MM


def mm_to_ldu(value: float) -> float:
    """Convert millimetres to LDU."""
    return value * MM_TO_LDU


def studs_to_ldu(studs: float) -> float:
    """Convert a stud-grid count to LDU (horizontal)."""
    return studs * STUD_SPACING_LDU


def ldu_to_studs(value: float) -> float:
    """Convert LDU to stud-grid units (horizontal)."""
    return value / STUD_SPACING_LDU


def plates_to_ldu(plates: float) -> float:
    """Convert a plate count to LDU (vertical)."""
    return plates * PLATE_HEIGHT_LDU


def ldu_to_plates(value: float) -> float:
    """Convert LDU to plate units (vertical)."""
    return value / PLATE_HEIGHT_LDU


def bricks_to_ldu(bricks: float) -> float:
    """Convert a brick count to LDU (vertical)."""
    return bricks * BRICK_HEIGHT_LDU


def ldu_to_bricks(value: float) -> float:
    """Convert LDU to brick units (vertical)."""
    return value / BRICK_HEIGHT_LDU


# ---------------------------------------------------------------------------
# Grid snapping
# ---------------------------------------------------------------------------

def snap_to_stud_grid(value: float) -> float:
    """Snap a single horizontal coordinate to the nearest stud grid line."""
    return round(value / STUD_SPACING_LDU) * STUD_SPACING_LDU


def snap_to_plate_grid(value: float) -> float:
    """Snap a vertical coordinate to the nearest plate height."""
    return round(value / PLATE_HEIGHT_LDU) * PLATE_HEIGHT_LDU


def snap_position(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """
    Snap (x, y, z) to the nearest valid grid position.

    X and Z are snapped to the stud grid; Y is snapped to the plate grid.
    """
    return snap_to_stud_grid(x), snap_to_plate_grid(y), snap_to_stud_grid(z)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def is_on_stud_grid(value: float) -> bool:
    """Return True if *value* lies on a stud grid line within tolerance."""
    remainder = math.fmod(abs(value), STUD_SPACING_LDU)
    return remainder < POSITION_TOLERANCE_LDU or (STUD_SPACING_LDU - remainder) < POSITION_TOLERANCE_LDU


def is_on_plate_grid(value: float) -> bool:
    """Return True if *value* lies on a plate-height grid line within tolerance."""
    remainder = math.fmod(abs(value), PLATE_HEIGHT_LDU)
    return remainder < POSITION_TOLERANCE_LDU or (PLATE_HEIGHT_LDU - remainder) < POSITION_TOLERANCE_LDU


def is_valid_grid_position(x: float, y: float, z: float) -> bool:
    """Return True if (x, y, z) is a valid snapped grid position."""
    return is_on_stud_grid(x) and is_on_plate_grid(y) and is_on_stud_grid(z)


# ---------------------------------------------------------------------------
# Convenience dataclass
# ---------------------------------------------------------------------------

@dataclass
class GridPosition:
    """
    An integer-indexed position on the LEGO grid.

    col / row  — stud-grid indices on the X / Z axes.
    layer      — plate-grid index on the Y axis.
    """
    col: int    # X stud index
    layer: int  # Y plate index
    row: int    # Z stud index

    def to_ldu(self) -> Tuple[float, float, float]:
        """Return the (x, y, z) LDU coordinates for this grid position."""
        return (
            studs_to_ldu(self.col),
            plates_to_ldu(self.layer),
            studs_to_ldu(self.row),
        )

    @staticmethod
    def from_ldu(x: float, y: float, z: float) -> "GridPosition":
        """Round LDU coordinates to the nearest grid position."""
        return GridPosition(
            col=round(ldu_to_studs(x)),
            layer=round(ldu_to_plates(y)),
            row=round(ldu_to_studs(z)),
        )
