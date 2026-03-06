import pytest
from brick_geometry.core.geometry import Point3D, Vector3D, BoundingBox
from brick_geometry.core.transforms import Pose
from brick_geometry.core.constants import STUD_SPACING_LDU, BRICK_HEIGHT_LDU, PLATE_HEIGHT_LDU
from brick_geometry.collision.bounding_box import (
    local_box_for_part, world_box, expanded_box, union_box, penetration_depth
)
from brick_geometry.parts.common_parts import BRICK_2x4, PLATE_2x4


class TestLocalBoxForPart:
    def test_origin_at_zero(self):
        bb = local_box_for_part(BRICK_2x4)
        assert bb.min_point == Point3D(0, 0, 0)

    def test_max_matches_dimensions(self):
        bb = local_box_for_part(BRICK_2x4)
        assert bb.max_point.x == pytest.approx(2 * STUD_SPACING_LDU)
        assert bb.max_point.y == pytest.approx(BRICK_HEIGHT_LDU)
        assert bb.max_point.z == pytest.approx(4 * STUD_SPACING_LDU)

    def test_plate_height(self):
        bb = local_box_for_part(PLATE_2x4)
        assert bb.max_point.y == pytest.approx(PLATE_HEIGHT_LDU)

    def test_include_studs_taller(self):
        without = local_box_for_part(BRICK_2x4, include_studs=False)
        with_studs = local_box_for_part(BRICK_2x4, include_studs=True)
        assert with_studs.max_point.y > without.max_point.y


class TestWorldBox:
    def test_translation(self):
        pose = Pose.from_xyz(100, 0, 0)
        bb = world_box(BRICK_2x4, pose)
        assert bb.min_point.x == pytest.approx(100)
        assert bb.max_point.x == pytest.approx(100 + 2 * STUD_SPACING_LDU)

    def test_identity_same_as_local(self):
        local = local_box_for_part(BRICK_2x4)
        w = world_box(BRICK_2x4, Pose.identity())
        assert w.min_point == local.min_point
        assert w.max_point == local.max_point


class TestExpandedBox:
    def test_expands_all_faces(self):
        bb = BoundingBox(Point3D(10, 10, 10), Point3D(20, 20, 20))
        exp = expanded_box(bb, 5)
        assert exp.min_point == Point3D(5, 5, 5)
        assert exp.max_point == Point3D(25, 25, 25)


class TestUnionBox:
    def test_two_boxes(self):
        a = BoundingBox(Point3D(0, 0, 0), Point3D(10, 10, 10))
        b = BoundingBox(Point3D(5, 5, 5), Point3D(20, 20, 20))
        u = union_box([a, b])
        assert u.min_point == Point3D(0, 0, 0)
        assert u.max_point == Point3D(20, 20, 20)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            union_box([])


class TestPenetrationDepth:
    def test_no_overlap_returns_zero(self):
        a = BoundingBox(Point3D(0, 0, 0), Point3D(10, 10, 10))
        b = BoundingBox(Point3D(20, 20, 20), Point3D(30, 30, 30))
        d = penetration_depth(a, b)
        assert d == Vector3D(0, 0, 0)

    def test_overlap_returns_nonzero(self):
        a = BoundingBox(Point3D(0, 0, 0), Point3D(15, 10, 10))
        b = BoundingBox(Point3D(10, 0, 0), Point3D(25, 10, 10))
        d = penetration_depth(a, b)
        assert d != Vector3D(0, 0, 0)
