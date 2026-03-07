"""
Input validation utilities for the LEGO geometry engine.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional, Sequence, Type, TypeVar

from ..core.constants import POSITION_TOLERANCE_LDU

F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# Primitive validators  (raise ValueError on failure)
# ---------------------------------------------------------------------------

def require_positive(value: float, name: str = "value") -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}.")


def require_non_negative(value: float, name: str = "value") -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}.")


def require_positive_int(value: int, name: str = "value") -> None:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}.")


def require_in_range(
    value: float, lo: float, hi: float, name: str = "value"
) -> None:
    if not (lo <= value <= hi):
        raise ValueError(f"{name} must be in [{lo}, {hi}], got {value}.")


def require_non_empty_string(value: str, name: str = "value") -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}.")


def require_instance(value: Any, expected_type: Type, name: str = "value") -> None:
    if not isinstance(value, expected_type):
        raise TypeError(
            f"{name} must be an instance of {expected_type.__name__}, "
            f"got {type(value).__name__}."
        )


def require_non_empty_sequence(seq: Sequence, name: str = "value") -> None:
    if len(seq) == 0:
        raise ValueError(f"{name} must not be empty.")


# ---------------------------------------------------------------------------
# Part-specific validators
# ---------------------------------------------------------------------------

def validate_part_id(part_id: str) -> str:
    """Return *part_id* stripped; raise ValueError if blank."""
    require_non_empty_string(part_id, "part_id")
    return part_id.strip()


def validate_stud_count(studs: int, axis: str = "studs") -> int:
    """Return *studs* if valid for Phase A (1–16); raise ValueError otherwise."""
    require_positive_int(studs, axis)
    if studs > 16:
        raise ValueError(f"{axis} count {studs} exceeds Phase-A limit of 16.")
    return studs


def validate_height_ldu(height: float) -> float:
    require_positive(height, "height_ldu")
    return height


# ---------------------------------------------------------------------------
# Pose / geometry validators
# ---------------------------------------------------------------------------

def validate_ldu_value(value: float, name: str = "value") -> float:
    """Raise ValueError if *value* is not a finite float."""
    import math
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value}.")
    return value


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def validated(func: F) -> F:
    """
    Decorator that converts TypeError / ValueError raised in *func* into
    a single consistent error message prefixed with the function name.

    Useful for public API entry points.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except (TypeError, ValueError) as exc:
            raise type(exc)(f"[{func.__qualname__}] {exc}") from exc

    return wrapper  # type: ignore[return-value]
