"""
Axis-aligned bounding box (AABB) construction for LEGO parts.

BoundingBox is defined in core/geometry.py; this module adds the
part-specific construction logic and transform helpers that sit on top of it.

All values are in LDU.  Part-local boxes are built from PartMetadata;
world-space boxes are obtained by transforming with a Pose.
"""

from __future__ import annotations

from typing import Sequence

from ..core.geometry import BoundingBox, Point3D, Vector3D
from ..core.transforms import Pose
from ..core.constants import POSITION_TOLERANCE_LDU, STUD_HEIGHT_LDU
from ..parts.part_metadata import PartMetadata


# ---------------------------------------------------------------------------
# Part-local AABB construction
# ---------------------------------------------------------------------------

def local_box_for_part(part: PartMetadata, include_studs: bool = False) -> BoundingBox:
    """
    Return the part-local AABB for *part*.

    The origin is at the bottom-front-left corner of the stud grid
    (min X, min Y, min Z).

    Parameters
    ----------
    part:
        The part whose box to build.
    include_studs:
        When True the box is tall enough to encompass the stud protrusions
        on the top face.  When False (default) the box covers only the main
        body — useful for checking whether two bodies physically overlap.
    """
    dims = part.dimensions
    max_y = dims.height_ldu + (STUD_HEIGHT_LDU if include_studs else 0.0)
    return BoundingBox(
        Point3D(0.0, 0.0, 0.0),
        Point3D(dims.width_ldu, max_y, dims.depth_ldu),
    )


# ---------------------------------------------------------------------------
# World-space AABB
# ---------------------------------------------------------------------------

def world_box(part: PartMetadata, pose: Pose, include_studs: bool = False) -> BoundingBox:
    """
    Transform the part-local AABB into world space using *pose*.

    Because Phase-A rotations are restricted to 90° steps the result is
    still axis-aligned (Pose.transform_bounding_box handles this).
    """
    local = local_box_for_part(part, include_studs=include_studs)
    return pose.transform_bounding_box(local)


# ---------------------------------------------------------------------------
# Swept / expanded boxes
# ---------------------------------------------------------------------------

def expanded_box(box: BoundingBox, margin: float) -> BoundingBox:
    """
    Return *box* grown by *margin* LDU on every face.

    Useful for broad-phase queries: two parts whose expanded boxes do *not*
    intersect cannot possibly collide.
    """
    return box.expanded(margin)


def union_box(boxes: Sequence[BoundingBox]) -> BoundingBox:
    """
    Return the smallest AABB that contains all boxes in *boxes*.

    Raises ValueError if *boxes* is empty.
    """
    if not boxes:
        raise ValueError("Cannot take the union of an empty sequence of boxes.")
    min_x = min(b.min_point.x for b in boxes)
    min_y = min(b.min_point.y for b in boxes)
    min_z = min(b.min_point.z for b in boxes)
    max_x = max(b.max_point.x for b in boxes)
    max_y = max(b.max_point.y for b in boxes)
    max_z = max(b.max_point.z for b in boxes)
    return BoundingBox(Point3D(min_x, min_y, min_z), Point3D(max_x, max_y, max_z))


# ---------------------------------------------------------------------------
# Penetration depth
# ---------------------------------------------------------------------------

def penetration_depth(a: BoundingBox, b: BoundingBox) -> Vector3D:
    """
    Return the minimum-translation vector needed to separate *a* from *b*.

    Returns the zero vector when the boxes do not overlap.
    Each component is the signed overlap on that axis (positive means *a*
    must move in the positive direction to separate).
    """
    def _overlap(a_min: float, a_max: float, b_min: float, b_max: float) -> float:
        # positive = overlap, negative = gap
        return min(a_max, b_max) - max(a_min, b_min)

    ox = _overlap(a.min_point.x, a.max_point.x, b.min_point.x, b.max_point.x)
    oy = _overlap(a.min_point.y, a.max_point.y, b.min_point.y, b.max_point.y)
    oz = _overlap(a.min_point.z, a.max_point.z, b.min_point.z, b.max_point.z)

    if ox <= POSITION_TOLERANCE_LDU or oy <= POSITION_TOLERANCE_LDU or oz <= POSITION_TOLERANCE_LDU:
        return Vector3D(0.0, 0.0, 0.0)

    # Push along the axis of minimum penetration.
    a_center_x = (a.min_point.x + a.max_point.x) / 2
    b_center_x = (b.min_point.x + b.max_point.x) / 2
    a_center_y = (a.min_point.y + a.max_point.y) / 2
    b_center_y = (b.min_point.y + b.max_point.y) / 2
    a_center_z = (a.min_point.z + a.max_point.z) / 2
    b_center_z = (b.min_point.z + b.max_point.z) / 2

    sign_x = 1.0 if a_center_x > b_center_x else -1.0
    sign_y = 1.0 if a_center_y > b_center_y else -1.0
    sign_z = 1.0 if a_center_z > b_center_z else -1.0

    if ox <= oy and ox <= oz:
        return Vector3D(sign_x * ox, 0.0, 0.0)
    if oy <= ox and oy <= oz:
        return Vector3D(0.0, sign_y * oy, 0.0)
    return Vector3D(0.0, 0.0, sign_z * oz)
