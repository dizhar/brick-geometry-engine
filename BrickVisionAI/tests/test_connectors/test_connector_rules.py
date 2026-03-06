import pytest
from brick_geometry.core.geometry import Point3D, Vector3D
from brick_geometry.connectors.connector_model import Connector, ConnectorType
from brick_geometry.connectors.connector_rules import (
    ConnectionRules, DEFAULT_RULES, types_are_compatible, ValidationResult
)


def make_stud(pos=None, normal=None):
    return Connector(
        connector_id="stud_0_0",
        connector_type=ConnectorType.STUD,
        position=pos or Point3D(10, 24, 10),
        normal=normal or Vector3D(0, 1, 0),
    )

def make_anti_stud(pos=None, normal=None):
    return Connector(
        connector_id="anti_stud_0_0",
        connector_type=ConnectorType.ANTI_STUD,
        position=pos or Point3D(10, 24, 10),
        normal=normal or Vector3D(0, -1, 0),
    )


class TestCompatibilityMatrix:
    def test_stud_anti_stud_compatible(self):
        assert types_are_compatible(ConnectorType.STUD, ConnectorType.ANTI_STUD)
        assert types_are_compatible(ConnectorType.ANTI_STUD, ConnectorType.STUD)

    def test_same_type_incompatible(self):
        assert not types_are_compatible(ConnectorType.STUD, ConnectorType.STUD)
        assert not types_are_compatible(ConnectorType.ANTI_STUD, ConnectorType.ANTI_STUD)


class TestValidationResult:
    def test_truthy(self):
        assert ValidationResult(True)
        assert not ValidationResult(False)

    def test_reason(self):
        r = ValidationResult(False, "bad alignment")
        assert "bad alignment" in repr(r)


class TestConnectionRules:
    def setup_method(self):
        self.rules = ConnectionRules()

    def test_valid_connection(self):
        s = make_stud(Point3D(10, 24, 10))
        a = make_anti_stud(Point3D(10, 24, 10))
        result = self.rules.validate(s, a)
        assert result.valid

    def test_incompatible_types(self):
        s1 = make_stud()
        s2 = Connector("stud_1_0", ConnectorType.STUD, Point3D(10, 24, 10), Vector3D(0, 1, 0))
        result = self.rules.check_type_compatibility(s1, s2)
        assert not result

    def test_occupied_fails(self):
        s = make_stud()
        a = make_anti_stud()
        a2 = make_anti_stud()
        s.occupy(a)
        result = self.rules.check_availability(s, a2)
        assert not result
        s.release()

    def test_misaligned_position_fails(self):
        s = make_stud(Point3D(0, 0, 0))
        a = make_anti_stud(Point3D(100, 100, 100))
        result = self.rules.check_alignment(s, a)
        assert not result

    def test_parallel_normals_fail(self):
        s = make_stud(normal=Vector3D(0, 1, 0))
        a = make_anti_stud(normal=Vector3D(0, 1, 0))  # same direction, not anti-parallel
        result = self.rules.check_normal_orientation(s, a)
        assert not result

    def test_anti_parallel_normals_pass(self):
        s = make_stud(normal=Vector3D(0, 1, 0))
        a = make_anti_stud(normal=Vector3D(0, -1, 0))
        result = self.rules.check_normal_orientation(s, a)
        assert result

    def test_form_connection(self):
        s = make_stud(Point3D(10, 24, 10))
        a = make_anti_stud(Point3D(10, 24, 10))
        pair = self.rules.form_connection(s, a)
        assert pair.stud is s
        assert pair.anti_stud is a
        assert not s.is_free
        assert not a.is_free

    def test_form_connection_invalid_raises(self):
        s1 = make_stud()
        s2 = Connector("s2", ConnectorType.STUD, Point3D(10, 24, 10), Vector3D(0, 1, 0))
        with pytest.raises(ValueError):
            self.rules.form_connection(s1, s2)

    def test_break_connection(self):
        s = make_stud(Point3D(10, 24, 10))
        a = make_anti_stud(Point3D(10, 24, 10))
        pair = self.rules.form_connection(s, a)
        self.rules.break_connection(pair)
        assert s.is_free
        assert a.is_free

    def test_score_perfect(self):
        s = make_stud(Point3D(10, 24, 10))
        a = make_anti_stud(Point3D(10, 24, 10))
        score = self.rules.connection_score(s, a)
        assert score == pytest.approx(1.0)

    def test_score_incompatible_zero(self):
        s1 = make_stud()
        s2 = Connector("s2", ConnectorType.STUD, Point3D(10, 24, 10), Vector3D(0, 1, 0))
        assert self.rules.connection_score(s1, s2) == 0.0

    def test_validate_batch(self):
        s = make_stud(Point3D(10, 24, 10))
        a = make_anti_stud(Point3D(10, 24, 10))
        results = self.rules.validate_batch([(s, a)])
        assert len(results) == 1
        assert results[0].valid
