import math
import pytest
from brick_geometry.core.geometry import Point3D, Vector3D, BoundingBox
from brick_geometry.core.constants import POSITION_TOLERANCE_LDU


class TestVector3D:
    def test_add(self):
        assert Vector3D(1, 2, 3) + Vector3D(4, 5, 6) == Vector3D(5, 7, 9)

    def test_sub(self):
        assert Vector3D(5, 7, 9) - Vector3D(4, 5, 6) == Vector3D(1, 2, 3)

    def test_mul_scalar(self):
        assert Vector3D(1, 2, 3) * 2 == Vector3D(2, 4, 6)
        assert 2 * Vector3D(1, 2, 3) == Vector3D(2, 4, 6)

    def test_div_scalar(self):
        assert Vector3D(2, 4, 6) / 2 == Vector3D(1, 2, 3)

    def test_neg(self):
        assert -Vector3D(1, -2, 3) == Vector3D(-1, 2, -3)

    def test_magnitude(self):
        assert math.isclose(Vector3D(3, 4, 0).magnitude(), 5.0)
        assert math.isclose(Vector3D(0, 0, 0).magnitude(), 0.0)

    def test_magnitude_sq(self):
        assert math.isclose(Vector3D(3, 4, 0).magnitude_sq(), 25.0)

    def test_normalize(self):
        n = Vector3D(3, 4, 0).normalize()
        assert math.isclose(n.magnitude(), 1.0, abs_tol=1e-9)

    def test_normalize_zero_raises(self):
        with pytest.raises(ValueError):
            Vector3D(0, 0, 0).normalize()

    def test_is_zero(self):
        assert Vector3D(0, 0, 0).is_zero()
        assert not Vector3D(0.1, 0, 0).is_zero()

    def test_dot(self):
        assert math.isclose(Vector3D(1, 0, 0).dot(Vector3D(0, 1, 0)), 0.0)
        assert math.isclose(Vector3D(1, 0, 0).dot(Vector3D(1, 0, 0)), 1.0)

    def test_cross(self):
        result = Vector3D(1, 0, 0).cross(Vector3D(0, 1, 0))
        assert result == Vector3D(0, 0, 1)

    def test_angle_to(self):
        angle = Vector3D(1, 0, 0).angle_to(Vector3D(0, 1, 0))
        assert math.isclose(angle, math.pi / 2)

    def test_unit_vectors(self):
        assert Vector3D.unit_x() == Vector3D(1, 0, 0)
        assert Vector3D.unit_y() == Vector3D(0, 1, 0)
        assert Vector3D.unit_z() == Vector3D(0, 0, 1)

    def test_equality_tolerance(self):
        tiny = POSITION_TOLERANCE_LDU / 2
        assert Vector3D(1, 2, 3) == Vector3D(1 + tiny, 2, 3)

    def test_to_tuple(self):
        assert Vector3D(1, 2, 3).to_tuple() == (1.0, 2.0, 3.0)


class TestPoint3D:
    def test_distance_to(self):
        assert math.isclose(Point3D(0, 0, 0).distance_to(Point3D(3, 4, 0)), 5.0)

    def test_distance_sq_to(self):
        assert math.isclose(Point3D(0, 0, 0).distance_sq_to(Point3D(3, 4, 0)), 25.0)

    def test_translate(self):
        p = Point3D(1, 2, 3).translate(Vector3D(1, 1, 1))
        assert p == Point3D(2, 3, 4)

    def test_add_vector(self):
        assert Point3D(1, 2, 3) + Vector3D(1, 0, 0) == Point3D(2, 2, 3)

    def test_vector_to(self):
        v = Point3D(0, 0, 0).vector_to(Point3D(1, 2, 3))
        assert v == Vector3D(1, 2, 3)

    def test_sub_gives_vector(self):
        v = Point3D(1, 2, 3) - Point3D(0, 0, 0)
        assert isinstance(v, Vector3D)
        assert v == Vector3D(1, 2, 3)

    def test_as_vector(self):
        assert Point3D(1, 2, 3).as_vector() == Vector3D(1, 2, 3)

    def test_origin(self):
        assert Point3D.origin() == Point3D(0, 0, 0)

    def test_equality_tolerance(self):
        tiny = POSITION_TOLERANCE_LDU / 2
        assert Point3D(0, 0, 0) == Point3D(tiny, 0, 0)

    def test_to_tuple(self):
        assert Point3D(1, 2, 3).to_tuple() == (1.0, 2.0, 3.0)


class TestBoundingBox:
    def test_size(self):
        bb = BoundingBox(Point3D(0, 0, 0), Point3D(40, 24, 80))
        assert bb.size == Vector3D(40, 24, 80)

    def test_center(self):
        bb = BoundingBox(Point3D(0, 0, 0), Point3D(40, 24, 80))
        assert bb.center == Point3D(20, 12, 40)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            BoundingBox(Point3D(10, 0, 0), Point3D(0, 0, 0))

    def test_contains(self):
        bb = BoundingBox(Point3D(0, 0, 0), Point3D(40, 24, 80))
        assert bb.contains(Point3D(20, 12, 40))
        assert not bb.contains(Point3D(50, 12, 40))

    def test_intersects_overlap(self):
        a = BoundingBox(Point3D(0, 0, 0), Point3D(40, 24, 80))
        b = BoundingBox(Point3D(20, 0, 0), Point3D(60, 24, 80))
        assert a.intersects(b)

    def test_intersects_touching_not_collision(self):
        # Touching boundary faces do NOT count as an intersection (LEGO side-by-side)
        a = BoundingBox(Point3D(0, 0, 0), Point3D(40, 24, 80))
        b = BoundingBox(Point3D(40, 0, 0), Point3D(80, 24, 80))
        assert not a.intersects(b)

    def test_no_intersect(self):
        a = BoundingBox(Point3D(0, 0, 0), Point3D(10, 10, 10))
        b = BoundingBox(Point3D(20, 20, 20), Point3D(30, 30, 30))
        assert not a.intersects(b)

    def test_expanded(self):
        bb = BoundingBox(Point3D(10, 10, 10), Point3D(20, 20, 20))
        exp = bb.expanded(5)
        assert exp.min_point == Point3D(5, 5, 5)
        assert exp.max_point == Point3D(25, 25, 25)

    def test_translated(self):
        bb = BoundingBox(Point3D(0, 0, 0), Point3D(10, 10, 10))
        moved = bb.translated(Vector3D(5, 0, 0))
        assert moved.min_point == Point3D(5, 0, 0)
        assert moved.max_point == Point3D(15, 10, 10)
