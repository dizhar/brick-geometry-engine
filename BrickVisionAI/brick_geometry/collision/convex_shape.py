"""
Convex shape representation and SAT-based narrow-phase collision for Phase B.

Phase A used AABB-vs-AABB for all parts.  That gives false positives for
slope parts: the rectangular AABB encompasses the empty wedge of air under
the sloped face, so neighbouring parts are incorrectly flagged as colliding.

Phase B introduces ConvexShape + Separating Axis Theorem (SAT):

  - Bricks / plates: continue to use AABB (already tight).
  - Slopes:          use a trapezoidal-prism ConvexShape; the slope-face
                     normal acts as the critical extra separating axis.

SAT correctness guarantee
-------------------------
Two convex polyhedra A and B do NOT intersect if and only if there exists a
separating hyperplane whose normal is one of:
  * a face normal of A
  * a face normal of B
  * a cross product of one edge direction of A with one edge direction of B

If no separating axis is found across all candidates the shapes overlap.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from ..core.geometry import BoundingBox, Point3D, Vector3D
from ..core.constants import POSITION_TOLERANCE_LDU
from ..core.transforms import Pose


# ---------------------------------------------------------------------------
# ConvexShape
# ---------------------------------------------------------------------------

@dataclass
class ConvexShape:
    """
    A convex polyhedron defined by vertices + unique face/edge directions.

    Attributes
    ----------
    vertices:
        All corner points of the polyhedron in *world* space.
    face_normals:
        One outward unit normal per unique face plane.
    edge_directions:
        One direction vector per unique edge axis (need not be unit vectors;
        SAT normalises before projection).
    """
    vertices: List[Point3D]
    face_normals: List[Vector3D]
    edge_directions: List[Vector3D]

    def project_onto(self, axis: Vector3D) -> Tuple[float, float]:
        """Project all vertices onto *axis*; return (min, max) scalar values."""
        projs = [axis.x * v.x + axis.y * v.y + axis.z * v.z for v in self.vertices]
        return min(projs), max(projs)


# ---------------------------------------------------------------------------
# SAT helpers
# ---------------------------------------------------------------------------

def _separated_on_axis(
    a: ConvexShape, b: ConvexShape, axis: Vector3D
) -> bool:
    """
    Return True if *axis* separates shapes *a* and *b* (no overlap).

    A tiny tolerance is subtracted so that touching-but-not-penetrating
    surfaces are NOT counted as collisions — this matches the behaviour of
    the AABB intersects() method which uses strict inequality.
    """
    mag_sq = axis.x ** 2 + axis.y ** 2 + axis.z ** 2
    if mag_sq < POSITION_TOLERANCE_LDU ** 2:
        return False  # degenerate (parallel edges) — skip

    inv_mag = 1.0 / math.sqrt(mag_sq)
    ax = Vector3D(axis.x * inv_mag, axis.y * inv_mag, axis.z * inv_mag)

    a_min, a_max = a.project_onto(ax)
    b_min, b_max = b.project_onto(ax)

    return (
        a_min >= b_max - POSITION_TOLERANCE_LDU
        or b_min >= a_max - POSITION_TOLERANCE_LDU
    )


def sat_intersect(a: ConvexShape, b: ConvexShape) -> bool:
    """
    Return True if convex shapes *a* and *b* intersect (SAT test).

    Returns False as soon as a separating axis is found (early exit).
    """
    # Face normals of A
    for n in a.face_normals:
        if _separated_on_axis(a, b, n):
            return False

    # Face normals of B
    for n in b.face_normals:
        if _separated_on_axis(a, b, n):
            return False

    # Edge-edge cross products
    for ea in a.edge_directions:
        for eb in b.edge_directions:
            axis = ea.cross(eb)
            if _separated_on_axis(a, b, axis):
                return False

    return True


# ---------------------------------------------------------------------------
# Factory: box from AABB
# ---------------------------------------------------------------------------

def box_shape_from_aabb(box: BoundingBox) -> ConvexShape:
    """Build a ConvexShape for an axis-aligned bounding box."""
    mn, mx = box.min_point, box.max_point
    vertices = [
        Point3D(mn.x, mn.y, mn.z), Point3D(mx.x, mn.y, mn.z),
        Point3D(mn.x, mx.y, mn.z), Point3D(mx.x, mx.y, mn.z),
        Point3D(mn.x, mn.y, mx.z), Point3D(mx.x, mn.y, mx.z),
        Point3D(mn.x, mx.y, mx.z), Point3D(mx.x, mx.y, mx.z),
    ]
    face_normals = [
        Vector3D(1, 0, 0), Vector3D(-1, 0, 0),
        Vector3D(0, 1, 0), Vector3D(0, -1, 0),
        Vector3D(0, 0, 1), Vector3D(0, 0, -1),
    ]
    edge_directions = [
        Vector3D(1, 0, 0),
        Vector3D(0, 1, 0),
        Vector3D(0, 0, 1),
    ]
    return ConvexShape(
        vertices=vertices,
        face_normals=face_normals,
        edge_directions=edge_directions,
    )


# ---------------------------------------------------------------------------
# Factory: slope trapezoidal prism
# ---------------------------------------------------------------------------

def slope_prism_shape(
    width_ldu: float,
    depth_ldu: float,
    height_low_ldu: float,
    height_high_ldu: float,
    pose: Pose,
) -> ConvexShape:
    """
    Build a world-space ConvexShape for a slope part.

    Local-space geometry
    --------------------
    The slope body is a trapezoidal prism whose cross-section in the YZ plane
    is a quadrilateral:

        (z=0, y=height_low)  ----slope face----  (z=depth, y=height_high)
              |                                         |
        (z=0, y=0)           ----bottom face----  (z=depth, y=0)

    Width runs along X in [0, width_ldu].

    Parameters
    ----------
    width_ldu:      X extent (studs_x × STUD_SPACING_LDU).
    depth_ldu:      Z extent (studs_z × STUD_SPACING_LDU).
    height_low_ldu: Height at z=0 (the low / front end).
    height_high_ldu: Height at z=depth (the high / back end).
    pose:           World-space pose; applied to all vertices and normals.
    """
    W = width_ldu
    D = depth_ldu
    H_lo = height_low_ldu
    H_hi = height_high_ldu
    dH = H_hi - H_lo

    # 8 vertices of the trapezoidal prism in local space
    local_verts: List[Point3D] = [
        Point3D(0, 0,    0),    # 0: front-bottom-left
        Point3D(W, 0,    0),    # 1: front-bottom-right
        Point3D(0, H_lo, 0),    # 2: front-top-left
        Point3D(W, H_lo, 0),    # 3: front-top-right
        Point3D(0, H_hi, D),    # 4: back-top-left
        Point3D(W, H_hi, D),    # 5: back-top-right
        Point3D(0, 0,    D),    # 6: back-bottom-left
        Point3D(W, 0,    D),    # 7: back-bottom-right
    ]

    slope_len = math.sqrt(D * D + dH * dH)
    if slope_len < POSITION_TOLERANCE_LDU:
        slope_len = 1.0  # degenerate guard

    # Face normals in local space (outward-pointing)
    # The slope face normal: the face goes from (z=0,y=H_lo) to (z=D,y=H_hi),
    # so face direction = (0, dH, D).  Outward normal (rotated 90° away from
    # body interior in the YZ plane) = (0, D, -dH) / slope_len.
    local_normals: List[Vector3D] = [
        Vector3D(0, -1, 0),                             # bottom
        Vector3D(0, 0, -1),                             # front (low end)
        Vector3D(0, 0, 1),                              # back (high end)
        Vector3D(-1, 0, 0),                             # left
        Vector3D(1, 0, 0),                              # right
        Vector3D(0, D / slope_len, -dH / slope_len),   # slope face
    ]

    # Unique edge directions in local space
    local_edges: List[Vector3D] = [
        Vector3D(1, 0, 0),                              # X (horizontal width)
        Vector3D(0, 0, 1),                              # Z (bottom / top-back)
        Vector3D(0, 1, 0),                              # Y (front face vertical)
        Vector3D(0, dH / slope_len, D / slope_len),    # slope face edge direction
    ]

    # Transform to world space
    vertices = [pose.transform_point(v) for v in local_verts]
    face_normals = [pose.transform_vector(n) for n in local_normals]
    edge_directions = [pose.transform_vector(e) for e in local_edges]

    return ConvexShape(
        vertices=vertices,
        face_normals=face_normals,
        edge_directions=edge_directions,
    )
