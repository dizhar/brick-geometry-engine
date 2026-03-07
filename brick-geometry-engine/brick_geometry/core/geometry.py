"""
Basic geometric primitives for the LEGO geometry engine.

All coordinates are in LDU (LEGO Drawing Units).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Tuple

from .constants import POSITION_TOLERANCE_LDU


# ---------------------------------------------------------------------------
# Vector3D
# ---------------------------------------------------------------------------

@dataclass
class Vector3D:
    x: float
    y: float
    z: float

    # --- arithmetic ---

    def __add__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3D:
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3D:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector3D:
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> Vector3D:
        return Vector3D(-self.x, -self.y, -self.z)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3D):
            return NotImplemented
        return (
            abs(self.x - other.x) < POSITION_TOLERANCE_LDU
            and abs(self.y - other.y) < POSITION_TOLERANCE_LDU
            and abs(self.z - other.z) < POSITION_TOLERANCE_LDU
        )

    # --- properties ---

    def magnitude(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def magnitude_sq(self) -> float:
        """Squared magnitude — avoids sqrt when only comparisons are needed."""
        return self.x ** 2 + self.y ** 2 + self.z ** 2

    def normalize(self) -> Vector3D:
        mag = self.magnitude()
        if mag < POSITION_TOLERANCE_LDU:
            raise ValueError("Cannot normalize a zero-length vector.")
        return self / mag

    def is_zero(self) -> bool:
        return self.magnitude_sq() < POSITION_TOLERANCE_LDU ** 2

    # --- operations ---

    def dot(self, other: Vector3D) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3D) -> Vector3D:
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def angle_to(self, other: Vector3D) -> float:
        """Return the angle in radians between this vector and *other*."""
        cos_theta = self.dot(other) / (self.magnitude() * other.magnitude())
        return math.acos(max(-1.0, min(1.0, cos_theta)))

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    # --- common unit vectors ---

    @staticmethod
    def zero() -> Vector3D:
        return Vector3D(0.0, 0.0, 0.0)

    @staticmethod
    def unit_x() -> Vector3D:
        return Vector3D(1.0, 0.0, 0.0)

    @staticmethod
    def unit_y() -> Vector3D:
        return Vector3D(0.0, 1.0, 0.0)

    @staticmethod
    def unit_z() -> Vector3D:
        return Vector3D(0.0, 0.0, 1.0)

    def __repr__(self) -> str:
        return f"Vector3D({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"


# ---------------------------------------------------------------------------
# Point3D
# ---------------------------------------------------------------------------

@dataclass
class Point3D:
    x: float
    y: float
    z: float

    def distance_to(self, other: Point3D) -> float:
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    def distance_sq_to(self, other: Point3D) -> float:
        """Squared distance — avoids sqrt when only comparisons are needed."""
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2

    def translate(self, v: Vector3D) -> Point3D:
        return Point3D(self.x + v.x, self.y + v.y, self.z + v.z)

    def vector_to(self, other: Point3D) -> Vector3D:
        """Return the vector from self to *other*."""
        return Vector3D(other.x - self.x, other.y - self.y, other.z - self.z)

    def as_vector(self) -> Vector3D:
        """Return the position vector from the origin to this point."""
        return Vector3D(self.x, self.y, self.z)

    def __sub__(self, other: Point3D) -> Vector3D:
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, v: Vector3D) -> Point3D:
        return self.translate(v)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point3D):
            return NotImplemented
        return (
            abs(self.x - other.x) < POSITION_TOLERANCE_LDU
            and abs(self.y - other.y) < POSITION_TOLERANCE_LDU
            and abs(self.z - other.z) < POSITION_TOLERANCE_LDU
        )

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @staticmethod
    def origin() -> Point3D:
        return Point3D(0.0, 0.0, 0.0)

    def __repr__(self) -> str:
        return f"Point3D({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"


# ---------------------------------------------------------------------------
# BoundingBox (axis-aligned)
# ---------------------------------------------------------------------------

@dataclass
class BoundingBox:
    """Axis-aligned bounding box defined by two corner points."""
    min_point: Point3D
    max_point: Point3D

    def __post_init__(self) -> None:
        if (
            self.min_point.x > self.max_point.x + POSITION_TOLERANCE_LDU
            or self.min_point.y > self.max_point.y + POSITION_TOLERANCE_LDU
            or self.min_point.z > self.max_point.z + POSITION_TOLERANCE_LDU
        ):
            raise ValueError("min_point must be <= max_point on all axes.")

    @property
    def size(self) -> Vector3D:
        return Vector3D(
            self.max_point.x - self.min_point.x,
            self.max_point.y - self.min_point.y,
            self.max_point.z - self.min_point.z,
        )

    @property
    def center(self) -> Point3D:
        return Point3D(
            (self.min_point.x + self.max_point.x) / 2,
            (self.min_point.y + self.max_point.y) / 2,
            (self.min_point.z + self.max_point.z) / 2,
        )

    def contains(self, point: Point3D) -> bool:
        return (
            self.min_point.x - POSITION_TOLERANCE_LDU <= point.x <= self.max_point.x + POSITION_TOLERANCE_LDU
            and self.min_point.y - POSITION_TOLERANCE_LDU <= point.y <= self.max_point.y + POSITION_TOLERANCE_LDU
            and self.min_point.z - POSITION_TOLERANCE_LDU <= point.z <= self.max_point.z + POSITION_TOLERANCE_LDU
        )

    def intersects(self, other: BoundingBox) -> bool:
        """Return True if this box strictly overlaps *other* (touching does not count)."""
        return (
            self.min_point.x < other.max_point.x - POSITION_TOLERANCE_LDU
            and self.max_point.x > other.min_point.x + POSITION_TOLERANCE_LDU
            and self.min_point.y < other.max_point.y - POSITION_TOLERANCE_LDU
            and self.max_point.y > other.min_point.y + POSITION_TOLERANCE_LDU
            and self.min_point.z < other.max_point.z - POSITION_TOLERANCE_LDU
            and self.max_point.z > other.min_point.z + POSITION_TOLERANCE_LDU
        )

    def expanded(self, amount: float) -> BoundingBox:
        """Return a new box expanded by *amount* on all sides."""
        v = Vector3D(amount, amount, amount)
        return BoundingBox(
            Point3D(self.min_point.x - amount, self.min_point.y - amount, self.min_point.z - amount),
            Point3D(self.max_point.x + amount, self.max_point.y + amount, self.max_point.z + amount),
        )

    def translated(self, v: Vector3D) -> BoundingBox:
        return BoundingBox(self.min_point + v, self.max_point + v)

    def __repr__(self) -> str:
        return f"BoundingBox(min={self.min_point}, max={self.max_point})"
