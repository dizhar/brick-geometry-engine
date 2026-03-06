"""
Pose and transformation system for the LEGO geometry engine.

Rotations are restricted to 90-degree increments around the X, Y, or Z axis
(Phase A constraint). Internally a rotation is stored as a 3×3 integer matrix
so there is no floating-point drift through repeated multiplications.

Coordinate convention (LDraw):
  X — right
  Y — up
  Z — toward viewer
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from .geometry import Point3D, Vector3D, BoundingBox
from .constants import POSITION_TOLERANCE_LDU


# ---------------------------------------------------------------------------
# 3×3 rotation matrix (integer entries for 90° steps)
# ---------------------------------------------------------------------------

# Row-major 3×3 stored as a flat 9-element tuple: (r00,r01,r02, r10,…, r22)
_Matrix3 = Tuple[
    int, int, int,
    int, int, int,
    int, int, int,
]

_IDENTITY_3: _Matrix3 = (
    1, 0, 0,
    0, 1, 0,
    0, 0, 1,
)

# 90° counter-clockwise rotations (right-hand rule) around each axis
_ROT_X_90: _Matrix3 = (
    1,  0,  0,
    0,  0, -1,
    0,  1,  0,
)
_ROT_Y_90: _Matrix3 = (
    0,  0,  1,
    0,  1,  0,
   -1,  0,  0,
)
_ROT_Z_90: _Matrix3 = (
    0, -1,  0,
    1,  0,  0,
    0,  0,  1,
)


def _mat3_mul(a: _Matrix3, b: _Matrix3) -> _Matrix3:
    """Multiply two 3×3 matrices (row-major flat tuples)."""
    return (
        a[0]*b[0] + a[1]*b[3] + a[2]*b[6],
        a[0]*b[1] + a[1]*b[4] + a[2]*b[7],
        a[0]*b[2] + a[1]*b[5] + a[2]*b[8],

        a[3]*b[0] + a[4]*b[3] + a[5]*b[6],
        a[3]*b[1] + a[4]*b[4] + a[5]*b[7],
        a[3]*b[2] + a[4]*b[5] + a[5]*b[8],

        a[6]*b[0] + a[7]*b[3] + a[8]*b[6],
        a[6]*b[1] + a[7]*b[4] + a[8]*b[7],
        a[6]*b[2] + a[7]*b[5] + a[8]*b[8],
    )


def _mat3_transpose(m: _Matrix3) -> _Matrix3:
    return (m[0], m[3], m[6], m[1], m[4], m[7], m[2], m[5], m[8])


def _mat3_apply(m: _Matrix3, v: Vector3D) -> Vector3D:
    return Vector3D(
        m[0]*v.x + m[1]*v.y + m[2]*v.z,
        m[3]*v.x + m[4]*v.y + m[5]*v.z,
        m[6]*v.x + m[7]*v.y + m[8]*v.z,
    )


# ---------------------------------------------------------------------------
# Rotation  (restricted to 90° increments)
# ---------------------------------------------------------------------------

class Rotation:
    """
    Orientation represented as a 3×3 rotation matrix with integer entries.

    Only multiples of 90° are representable; attempting arbitrary angles
    raises ValueError.
    """

    __slots__ = ("_mat",)

    def __init__(self, mat: _Matrix3 = _IDENTITY_3) -> None:
        self._mat: _Matrix3 = mat

    # --- factory helpers ---

    @staticmethod
    def identity() -> Rotation:
        return Rotation(_IDENTITY_3)

    @staticmethod
    def from_axis_angle_90(axis: str, steps: int) -> Rotation:
        """
        Build a rotation from *steps* × 90° around *axis* ('x', 'y', or 'z').

        Positive steps follow the right-hand rule.
        """
        axis = axis.lower()
        if axis not in ("x", "y", "z"):
            raise ValueError(f"axis must be 'x', 'y', or 'z', got {axis!r}")
        steps = steps % 4
        base = {"x": _ROT_X_90, "y": _ROT_Y_90, "z": _ROT_Z_90}[axis]
        mat: _Matrix3 = _IDENTITY_3
        for _ in range(steps):
            mat = _mat3_mul(mat, base)
        return Rotation(mat)

    # --- composition ---

    def compose(self, other: Rotation) -> Rotation:
        """Return the rotation that first applies *self* then *other*."""
        return Rotation(_mat3_mul(other._mat, self._mat))

    def inverse(self) -> Rotation:
        """For orthogonal matrices the inverse equals the transpose."""
        return Rotation(_mat3_transpose(self._mat))

    # --- application ---

    def apply(self, v: Vector3D) -> Vector3D:
        """Rotate a vector."""
        return _mat3_apply(self._mat, v)

    def apply_point(self, p: Point3D) -> Point3D:
        """Rotate a point around the origin."""
        v = _mat3_apply(self._mat, Vector3D(p.x, p.y, p.z))
        return Point3D(v.x, v.y, v.z)

    # --- comparison ---

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rotation):
            return NotImplemented
        return self._mat == other._mat

    def __repr__(self) -> str:
        m = self._mat
        return (
            f"Rotation([\n"
            f"  [{m[0]:2d}, {m[1]:2d}, {m[2]:2d}],\n"
            f"  [{m[3]:2d}, {m[4]:2d}, {m[5]:2d}],\n"
            f"  [{m[6]:2d}, {m[7]:2d}, {m[8]:2d}]\n"
            f"])"
        )


# ---------------------------------------------------------------------------
# Pose  (position + rotation)
# ---------------------------------------------------------------------------

@dataclass
class Pose:
    """
    Full 6-DOF pose: a 3-D position (LDU) plus a Rotation.

    Phase A: rotation is restricted to 90° increments.
    """
    position: Point3D = field(default_factory=Point3D.origin)
    rotation: Rotation = field(default_factory=Rotation.identity)

    # --- factory ---

    @staticmethod
    def identity() -> Pose:
        return Pose(Point3D.origin(), Rotation.identity())

    @staticmethod
    def from_xyz(x: float, y: float, z: float) -> Pose:
        return Pose(Point3D(x, y, z), Rotation.identity())

    # --- composition ---

    def compose(self, other: Pose) -> Pose:
        """
        Return the pose that results from applying *other* in the local frame
        of *self*.  Equivalent to: T_self * T_other.
        """
        new_position = self.position + self.rotation.apply(
            Vector3D(other.position.x, other.position.y, other.position.z)
        )
        new_rotation = self.rotation.compose(other.rotation)
        return Pose(new_position, new_rotation)

    def inverse(self) -> Pose:
        """Return the inverse pose so that pose.compose(pose.inverse()) == identity."""
        inv_rot = self.rotation.inverse()
        inv_pos = inv_rot.apply(-Vector3D(self.position.x, self.position.y, self.position.z))
        return Pose(Point3D(inv_pos.x, inv_pos.y, inv_pos.z), inv_rot)

    # --- application ---

    def transform_point(self, p: Point3D) -> Point3D:
        """Apply this pose to a point (rotate then translate)."""
        rotated = self.rotation.apply_point(p)
        return rotated + Vector3D(self.position.x, self.position.y, self.position.z)

    def transform_vector(self, v: Vector3D) -> Vector3D:
        """Apply only the rotation component to a vector (no translation)."""
        return self.rotation.apply(v)

    def transform_bounding_box(self, bb: BoundingBox) -> BoundingBox:
        """
        Transform a bounding box by this pose.

        Because the rotation is restricted to 90° steps the result is still
        axis-aligned — all eight corners are transformed and the new AABB
        is taken from their extremes.
        """
        corners = [
            Point3D(bb.min_point.x, bb.min_point.y, bb.min_point.z),
            Point3D(bb.max_point.x, bb.min_point.y, bb.min_point.z),
            Point3D(bb.min_point.x, bb.max_point.y, bb.min_point.z),
            Point3D(bb.min_point.x, bb.min_point.y, bb.max_point.z),
            Point3D(bb.max_point.x, bb.max_point.y, bb.min_point.z),
            Point3D(bb.max_point.x, bb.min_point.y, bb.max_point.z),
            Point3D(bb.min_point.x, bb.max_point.y, bb.max_point.z),
            Point3D(bb.max_point.x, bb.max_point.y, bb.max_point.z),
        ]
        transformed = [self.transform_point(c) for c in corners]
        xs = [c.x for c in transformed]
        ys = [c.y for c in transformed]
        zs = [c.z for c in transformed]
        return BoundingBox(
            Point3D(min(xs), min(ys), min(zs)),
            Point3D(max(xs), max(ys), max(zs)),
        )

    # --- relative pose ---

    def relative_to(self, reference: Pose) -> Pose:
        """Express this pose in the local frame of *reference*."""
        return reference.inverse().compose(self)

    # --- comparison ---

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Pose):
            return NotImplemented
        return self.position == other.position and self.rotation == other.rotation

    def __repr__(self) -> str:
        return f"Pose(position={self.position!r}, rotation={self.rotation!r})"
