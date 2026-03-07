import math
import pytest
from brick_geometry.core.geometry import Point3D, Vector3D, BoundingBox
from brick_geometry.core.transforms import Rotation, Pose


class TestRotation:
    def test_identity_apply(self):
        r = Rotation.identity()
        v = Vector3D(1, 2, 3)
        assert r.apply(v) == v

    def test_rotate_y_90(self):
        r = Rotation.from_axis_angle_90("y", 1)
        # +X rotated 90° CCW around Y → −Z
        result = r.apply(Vector3D(1, 0, 0))
        assert result == Vector3D(0, 0, -1)

    def test_rotate_y_180(self):
        r = Rotation.from_axis_angle_90("y", 2)
        result = r.apply(Vector3D(1, 0, 0))
        assert result == Vector3D(-1, 0, 0)

    def test_rotate_y_270(self):
        r = Rotation.from_axis_angle_90("y", 3)
        result = r.apply(Vector3D(1, 0, 0))
        assert result == Vector3D(0, 0, 1)

    def test_rotate_x_90(self):
        r = Rotation.from_axis_angle_90("x", 1)
        # +Y rotated 90° CCW around X → +Z
        result = r.apply(Vector3D(0, 1, 0))
        assert result == Vector3D(0, 0, 1)

    def test_rotate_z_90(self):
        r = Rotation.from_axis_angle_90("z", 1)
        # +X rotated 90° CCW around Z → +Y
        result = r.apply(Vector3D(1, 0, 0))
        assert result == Vector3D(0, 1, 0)

    def test_four_rotations_returns_identity(self):
        r = Rotation.from_axis_angle_90("y", 4)
        assert r == Rotation.identity()

    def test_steps_mod_4(self):
        r5 = Rotation.from_axis_angle_90("y", 5)
        r1 = Rotation.from_axis_angle_90("y", 1)
        assert r5 == r1

    def test_invalid_axis_raises(self):
        with pytest.raises(ValueError):
            Rotation.from_axis_angle_90("w", 1)

    def test_inverse_undoes_rotation(self):
        r = Rotation.from_axis_angle_90("y", 1)
        v = Vector3D(1, 2, 3)
        assert r.inverse().apply(r.apply(v)) == v

    def test_compose(self):
        r1 = Rotation.from_axis_angle_90("y", 1)
        r2 = Rotation.from_axis_angle_90("y", 1)
        r_composed = r1.compose(r2)
        r_double = Rotation.from_axis_angle_90("y", 2)
        v = Vector3D(1, 0, 0)
        assert r_composed.apply(v) == r_double.apply(v)

    def test_apply_point(self):
        r = Rotation.from_axis_angle_90("y", 1)
        p = Point3D(1, 0, 0)
        result = r.apply_point(p)
        assert result == Point3D(0, 0, -1)

    def test_equality(self):
        assert Rotation.identity() == Rotation.identity()
        r1 = Rotation.from_axis_angle_90("y", 1)
        r2 = Rotation.from_axis_angle_90("y", 1)
        assert r1 == r2
        assert r1 != Rotation.from_axis_angle_90("y", 2)


class TestPose:
    def test_identity(self):
        p = Pose.identity()
        pt = Point3D(1, 2, 3)
        assert p.transform_point(pt) == pt

    def test_from_xyz(self):
        p = Pose.from_xyz(10, 20, 30)
        assert p.position == Point3D(10, 20, 30)
        assert p.rotation == Rotation.identity()

    def test_transform_point_translation_only(self):
        p = Pose.from_xyz(5, 0, 0)
        assert p.transform_point(Point3D(0, 0, 0)) == Point3D(5, 0, 0)
        assert p.transform_point(Point3D(1, 0, 0)) == Point3D(6, 0, 0)

    def test_transform_point_rotation_only(self):
        p = Pose(Point3D.origin(), Rotation.from_axis_angle_90("y", 1))
        result = p.transform_point(Point3D(1, 0, 0))
        assert result == Point3D(0, 0, -1)

    def test_transform_point_rotation_then_translation(self):
        p = Pose(Point3D(10, 0, 0), Rotation.from_axis_angle_90("y", 1))
        result = p.transform_point(Point3D(1, 0, 0))
        assert result == Point3D(10, 0, -1)

    def test_transform_vector_no_translation(self):
        p = Pose.from_xyz(100, 100, 100)
        v = Vector3D(1, 0, 0)
        assert p.transform_vector(v) == v

    def test_inverse(self):
        p = Pose(Point3D(10, 20, 30), Rotation.from_axis_angle_90("y", 1))
        pt = Point3D(5, 5, 5)
        roundtrip = p.inverse().transform_point(p.transform_point(pt))
        assert roundtrip == pt

    def test_compose(self):
        p1 = Pose.from_xyz(10, 0, 0)
        p2 = Pose.from_xyz(5, 0, 0)
        composed = p1.compose(p2)
        assert composed.transform_point(Point3D.origin()) == Point3D(15, 0, 0)

    def test_relative_to(self):
        world = Pose.from_xyz(10, 0, 0)
        child = Pose.from_xyz(15, 0, 0)
        rel = child.relative_to(world)
        assert rel.position == Point3D(5, 0, 0)

    def test_transform_bounding_box_translation(self):
        p = Pose.from_xyz(10, 0, 0)
        bb = BoundingBox(Point3D(0, 0, 0), Point3D(40, 24, 80))
        result = p.transform_bounding_box(bb)
        assert result.min_point == Point3D(10, 0, 0)
        assert result.max_point == Point3D(50, 24, 80)

    def test_transform_bounding_box_rotation_stays_aabb(self):
        p = Pose(Point3D.origin(), Rotation.from_axis_angle_90("y", 1))
        bb = BoundingBox(Point3D(0, 0, 0), Point3D(40, 24, 80))
        result = p.transform_bounding_box(bb)
        # _ROT_Y_90 maps (x,y,z) → (z, y, -x)
        # x range 0..40 → new_z: 0..-40  →  z: -40..0
        # z range 0..80 → new_x: 0..80   →  x:   0..80
        assert result.min_point.x == pytest.approx(0, abs=1e-6)
        assert result.max_point.x == pytest.approx(80, abs=1e-6)
        assert result.min_point.z == pytest.approx(-40, abs=1e-6)
        assert result.max_point.z == pytest.approx(0, abs=1e-6)

    def test_equality(self):
        assert Pose.identity() == Pose.identity()
        assert Pose.from_xyz(1, 0, 0) != Pose.from_xyz(2, 0, 0)
