"""
Tests for Phase B ConvexShape and SAT-based collision.

The key scenario validated here is the false-positive that AABB produces
for slopes: a part placed entirely above the slope face (in the empty wedge
under the slope's AABB) should NOT be reported as colliding.
"""

import pytest
import math
from brick_geometry.core.geometry import BoundingBox, Point3D, Vector3D
from brick_geometry.core.transforms import Pose
from brick_geometry.collision.convex_shape import (
    ConvexShape,
    box_shape_from_aabb,
    slope_prism_shape,
    sat_intersect,
    _separated_on_axis,
)
from brick_geometry.core.constants import (
    STUD_SPACING_LDU, BRICK_HEIGHT_LDU, PLATE_HEIGHT_LDU,
)


# ---------------------------------------------------------------------------
# ConvexShape.project_onto
# ---------------------------------------------------------------------------

class TestProjectOnto:
    def _unit_cube(self) -> ConvexShape:
        box = BoundingBox(Point3D(0, 0, 0), Point3D(1, 1, 1))
        return box_shape_from_aabb(box)

    def test_project_x_axis(self):
        s = self._unit_cube()
        lo, hi = s.project_onto(Vector3D(1, 0, 0))
        assert lo == pytest.approx(0.0)
        assert hi == pytest.approx(1.0)

    def test_project_diagonal(self):
        s = self._unit_cube()
        # Projection onto (1,1,0)/sqrt(2): expect [0, sqrt(2)]
        axis = Vector3D(1 / math.sqrt(2), 1 / math.sqrt(2), 0)
        lo, hi = s.project_onto(axis)
        assert lo == pytest.approx(0.0)
        assert hi == pytest.approx(math.sqrt(2))


# ---------------------------------------------------------------------------
# box_shape_from_aabb
# ---------------------------------------------------------------------------

class TestBoxShapeFromAABB:
    def test_vertex_count(self):
        box = BoundingBox(Point3D(0, 0, 0), Point3D(10, 20, 30))
        s = box_shape_from_aabb(box)
        assert len(s.vertices) == 8

    def test_face_normal_count(self):
        box = BoundingBox(Point3D(0, 0, 0), Point3D(10, 20, 30))
        s = box_shape_from_aabb(box)
        assert len(s.face_normals) == 6

    def test_edge_direction_count(self):
        box = BoundingBox(Point3D(0, 0, 0), Point3D(10, 20, 30))
        s = box_shape_from_aabb(box)
        assert len(s.edge_directions) == 3


# ---------------------------------------------------------------------------
# SAT: box vs box
# ---------------------------------------------------------------------------

class TestSATBoxBox:
    def _box(self, x0, y0, z0, x1, y1, z1) -> ConvexShape:
        return box_shape_from_aabb(
            BoundingBox(Point3D(x0, y0, z0), Point3D(x1, y1, z1))
        )

    def test_same_box_intersects(self):
        b = self._box(0, 0, 0, 10, 10, 10)
        assert sat_intersect(b, b)

    def test_overlapping_boxes_intersect(self):
        a = self._box(0, 0, 0, 10, 10, 10)
        b = self._box(5, 5, 5, 15, 15, 15)
        assert sat_intersect(a, b)

    def test_separated_x(self):
        a = self._box(0, 0, 0, 10, 10, 10)
        b = self._box(20, 0, 0, 30, 10, 10)
        assert not sat_intersect(a, b)

    def test_separated_y(self):
        a = self._box(0, 0, 0, 10, 10, 10)
        b = self._box(0, 20, 0, 10, 30, 10)
        assert not sat_intersect(a, b)

    def test_separated_z(self):
        a = self._box(0, 0, 0, 10, 10, 10)
        b = self._box(0, 0, 20, 10, 10, 30)
        assert not sat_intersect(a, b)

    def test_touching_on_face_not_intersecting(self):
        # Two cubes that share exactly one face — touching but NOT penetrating.
        a = self._box(0, 0, 0, 10, 10, 10)
        b = self._box(10, 0, 0, 20, 10, 10)
        # Touching only: sat_intersect should return False (strict inequality).
        assert not sat_intersect(a, b)

    def test_partial_x_overlap(self):
        a = self._box(0, 0, 0, 10, 10, 10)
        b = self._box(9, 0, 0, 19, 10, 10)   # 1 unit overlap in X
        assert sat_intersect(a, b)


# ---------------------------------------------------------------------------
# SAT: slope prism vs box  (the key Phase B scenario)
# ---------------------------------------------------------------------------

class TestSATSlopeVsBox:
    """
    Slope geometry (local space, H_lo=0, H_hi=24, depth=40):
        Front edge (z=0): height 0  (floor level)
        Back  edge (z=40): height 24 (1 brick)

    A box placed ABOVE the slope face (in the empty wedge region) should NOT
    collide even though their AABBs overlap.
    """

    def _slope_at_origin(self) -> ConvexShape:
        """Slope prism: 1 stud wide, 2 studs deep, rising from 0 to 24 LDU."""
        return slope_prism_shape(
            width_ldu=float(STUD_SPACING_LDU),    # 20
            depth_ldu=2 * float(STUD_SPACING_LDU), # 40
            height_low_ldu=0.0,
            height_high_ldu=float(BRICK_HEIGHT_LDU),  # 24
            pose=Pose.identity(),
        )

    def _box_at(self, x0, y0, z0, x1, y1, z1) -> ConvexShape:
        return box_shape_from_aabb(
            BoundingBox(Point3D(x0, y0, z0), Point3D(x1, y1, z1))
        )

    def test_slope_vs_overlapping_brick_collides(self):
        """A brick that genuinely overlaps the slope body collides."""
        slope = self._slope_at_origin()
        # 1×1 plate (8 LDU tall) sitting at the base of the slope:
        # y=0..8, z=0..20 — the slope body is thick here (y=0..z*0.6).
        brick = self._box_at(0, 0, 0, 20, 8, 20)
        assert sat_intersect(slope, brick)

    def test_slope_vs_box_in_empty_wedge_no_collision(self):
        """
        A box placed entirely inside the empty wedge above the slope (where
        the AABB claims the slope is present but the actual prism is not)
        should NOT collide.

        At z=0 the slope has height=0.  A 1-stud plate at y=16..24, z=0..20
        is entirely above the slope surface at z=0..20.
        """
        slope = self._slope_at_origin()
        # This box sits at y=16 to y=24, z=0 to z=20.
        # Slope AABB = (0,0,0)-(20,24,40): AABB says COLLISION.
        # Actual prism: at z=20 the slope height = 24*(20/40)=12 < 16. NO collision.
        box_above_slope = self._box_at(0, 16, 0, 20, 24, 20)
        assert not sat_intersect(slope, box_above_slope)

    def test_slope_vs_box_behind_fully_collides(self):
        """Box fully inside the slope body at the high (back) end collides."""
        slope = self._slope_at_origin()
        box_inside = self._box_at(0, 0, 30, 20, 20, 40)
        assert sat_intersect(slope, box_inside)

    def test_slope_vs_box_completely_beside_no_collision(self):
        """Box far to the side (X direction) — clearly separated."""
        slope = self._slope_at_origin()
        box_side = self._box_at(100, 0, 0, 120, 24, 40)
        assert not sat_intersect(slope, box_side)

    def test_slope_vs_box_directly_above_no_collision(self):
        """Box floating above the slope (y > 24) doesn't collide."""
        slope = self._slope_at_origin()
        box_above = self._box_at(0, 30, 0, 20, 40, 40)
        assert not sat_intersect(slope, box_above)

    def test_slope_with_h_low_plate_height_wedge_above_face(self):
        """
        Slope rising from 1 plate (8 LDU) to 1 brick (24 LDU) over 40 LDU depth.

        slope_height(z) = 8 + 16*(z/40)
          At z=0:  h=8
          At z=20: h=16

        A box at y=20..28, z=0..20 is entirely above the slope face for that
        Z range (slope never reaches y=20 until z=30). AABB says collision
        (y=20 < AABB top=24); SAT correctly finds no collision.
        """
        slope = slope_prism_shape(
            width_ldu=20.0,
            depth_ldu=40.0,
            height_low_ldu=float(PLATE_HEIGHT_LDU),   # 8
            height_high_ldu=float(BRICK_HEIGHT_LDU),   # 24
            pose=Pose.identity(),
        )
        # Box above slope face: y=20..28, z=0..20.
        # At z=20 the slope height is only 16 < 20. No penetration.
        box_above_face = self._box_at(0, 20, 0, 20, 28, 20)
        assert not sat_intersect(slope, box_above_face)

    def test_slope_with_h_low_plate_height_inside_body(self):
        """A box at y=0..7, z=0..20 is inside the slope body (front rectangular portion)."""
        slope = slope_prism_shape(
            width_ldu=20.0,
            depth_ldu=40.0,
            height_low_ldu=float(PLATE_HEIGHT_LDU),
            height_high_ldu=float(BRICK_HEIGHT_LDU),
            pose=Pose.identity(),
        )
        # The slope front face height is 8 LDU. A box from y=0..7 sits
        # inside the slope body and must be flagged as colliding.
        box_inside = self._box_at(0, 0, 0, 20, 7, 20)
        assert sat_intersect(slope, box_inside)

    def test_slope_vs_slope_no_collision_side_by_side(self):
        """Two identical slopes placed side by side (X direction) don't collide."""
        slope_a = slope_prism_shape(
            width_ldu=20.0, depth_ldu=40.0,
            height_low_ldu=0.0, height_high_ldu=24.0,
            pose=Pose.identity(),
        )
        slope_b = slope_prism_shape(
            width_ldu=20.0, depth_ldu=40.0,
            height_low_ldu=0.0, height_high_ldu=24.0,
            pose=Pose.from_xyz(20.0, 0.0, 0.0),  # shifted 1 stud in X
        )
        assert not sat_intersect(slope_a, slope_b)

    def test_slope_vs_slope_stacked_collides(self):
        """Two identical slope prisms at the same position collide."""
        pose = Pose.identity()
        slope = slope_prism_shape(20.0, 40.0, 0.0, 24.0, pose)
        assert sat_intersect(slope, slope)


# ---------------------------------------------------------------------------
# slope_prism_shape: geometry sanity checks
# ---------------------------------------------------------------------------

class TestSlopePrismShape:
    def test_vertex_count(self):
        s = slope_prism_shape(20.0, 40.0, 0.0, 24.0, Pose.identity())
        assert len(s.vertices) == 8

    def test_face_normal_count(self):
        s = slope_prism_shape(20.0, 40.0, 0.0, 24.0, Pose.identity())
        assert len(s.face_normals) == 6

    def test_flat_slope_degenerate_guard(self):
        """A zero-height slope (H_lo == H_hi) should not crash."""
        s = slope_prism_shape(20.0, 40.0, 24.0, 24.0, Pose.identity())
        # With degenerate slope, SAT still runs without error.
        box = box_shape_from_aabb(BoundingBox(Point3D(0, 0, 0), Point3D(20, 24, 40)))
        # They overlap (identical volumes); just check no exception.
        sat_intersect(s, box)

    def test_pose_translation_applied(self):
        """Slope prism translated in X should have shifted vertex X coordinates."""
        s = slope_prism_shape(20.0, 40.0, 0.0, 24.0, Pose.from_xyz(100.0, 0.0, 0.0))
        xs = [v.x for v in s.vertices]
        assert min(xs) == pytest.approx(100.0)
        assert max(xs) == pytest.approx(120.0)
