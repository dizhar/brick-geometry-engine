"""
Mathematical utilities for the LEGO geometry engine.
"""

from __future__ import annotations

import math
from typing import Sequence

from ..core.constants import POSITION_TOLERANCE_LDU


# ---------------------------------------------------------------------------
# Floating-point comparison
# ---------------------------------------------------------------------------

def approx_equal(a: float, b: float, tol: float = POSITION_TOLERANCE_LDU) -> bool:
    return abs(a - b) <= tol


def approx_zero(value: float, tol: float = POSITION_TOLERANCE_LDU) -> bool:
    return abs(value) <= tol


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Angle helpers
# ---------------------------------------------------------------------------

def deg_to_rad(degrees: float) -> float:
    return math.radians(degrees)


def rad_to_deg(radians: float) -> float:
    return math.degrees(radians)


def snap_to_90(degrees: float) -> int:
    """Round *degrees* to the nearest multiple of 90."""
    return round(degrees / 90) * 90


def is_multiple_of_90(degrees: float, tol: float = 0.01) -> bool:
    remainder = math.fmod(abs(degrees), 90.0)
    return remainder < tol or (90.0 - remainder) < tol


# ---------------------------------------------------------------------------
# Numeric utilities
# ---------------------------------------------------------------------------

def sign(value: float) -> float:
    """Return −1, 0, or +1."""
    if approx_zero(value):
        return 0.0
    return 1.0 if value > 0 else -1.0


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* at parameter *t* ∈ [0, 1]."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def snap_to_grid(value: float, grid_size: float) -> float:
    """Snap *value* to the nearest multiple of *grid_size*."""
    if approx_zero(grid_size):
        raise ValueError("grid_size must not be zero.")
    return round(value / grid_size) * grid_size


def is_on_grid(value: float, grid_size: float, tol: float = POSITION_TOLERANCE_LDU) -> bool:
    remainder = math.fmod(abs(value), grid_size)
    return remainder < tol or (grid_size - remainder) < tol


# ---------------------------------------------------------------------------
# Safe trigonometry
# ---------------------------------------------------------------------------

def safe_acos(value: float) -> float:
    """acos clamped to [−1, 1] to avoid domain errors from float rounding."""
    return math.acos(clamp(value, -1.0, 1.0))


def safe_asin(value: float) -> float:
    """asin clamped to [−1, 1] to avoid domain errors from float rounding."""
    return math.asin(clamp(value, -1.0, 1.0))


# ---------------------------------------------------------------------------
# Sequence helpers
# ---------------------------------------------------------------------------

def all_approx_equal(values: Sequence[float], tol: float = POSITION_TOLERANCE_LDU) -> bool:
    """Return True if all values in *values* are within *tol* of each other."""
    if len(values) < 2:
        return True
    return max(values) - min(values) <= tol
