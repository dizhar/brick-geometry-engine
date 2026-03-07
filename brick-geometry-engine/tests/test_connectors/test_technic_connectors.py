"""Tests for Phase B Technic connector types, rules, and part generation."""

import pytest
from brick_geometry.connectors.connector_model import (
    Connector, ConnectorPair, ConnectorType, ConnectorState,
)
from brick_geometry.connectors.connector_rules import (
    ConnectionRules, DEFAULT_RULES, types_are_compatible, _is_technic_pair,
)
from brick_geometry.core.geometry import Point3D, Vector3D
from brick_geometry.core.transforms import Pose
from brick_geometry.parts.technic_parts import (
    ALL_TECHNIC,
    TECHNIC_BRICK_1x2,
    TECHNIC_BRICK_1x4,
    get_technic_part,
)
from brick_geometry.parts.part_metadata import PartCategory, TechnicGeometry
from brick_geometry.assembly.assembly_node import generate_connectors
from brick_geometry.core.constants import BRICK_HEIGHT_LDU, STUD_SPACING_LDU


# ---------------------------------------------------------------------------
# ConnectorType additions
# ---------------------------------------------------------------------------

class TestNewConnectorTypes:
    def test_technic_types_exist(self):
        assert hasattr(ConnectorType, "TECHNIC_PIN")
        assert hasattr(ConnectorType, "TECHNIC_HOLE")
        assert hasattr(ConnectorType, "TECHNIC_AXLE")
        assert hasattr(ConnectorType, "TECHNIC_AXLE_HOLE")

    def test_technic_hole_height_zero(self):
        c = Connector(
            connector_id="hole_0_0_pos",
            connector_type=ConnectorType.TECHNIC_HOLE,
            position=Point3D(10, 12, 10),
            normal=Vector3D(1, 0, 0),
        )
        assert c.height == pytest.approx(0.0)

    def test_technic_pin_height_zero(self):
        c = Connector(
            connector_id="pin",
            connector_type=ConnectorType.TECHNIC_PIN,
            position=Point3D(0, 12, 10),
            normal=Vector3D(1, 0, 0),
        )
        assert c.height == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# ConnectorPair with Technic types
# ---------------------------------------------------------------------------

class TestTechnicConnectorPair:
    def _pin(self, cid="pin"):
        return Connector(cid, ConnectorType.TECHNIC_PIN, Point3D(0, 12, 10), Vector3D(1, 0, 0))

    def _hole(self, cid="hole"):
        return Connector(cid, ConnectorType.TECHNIC_HOLE, Point3D(0, 12, 10), Vector3D(-1, 0, 0))

    def test_pin_hole_pair_valid(self):
        pair = ConnectorPair(stud=self._pin(), anti_stud=self._hole())
        assert pair.stud.connector_type == ConnectorType.TECHNIC_PIN
        assert pair.anti_stud.connector_type == ConnectorType.TECHNIC_HOLE

    def test_hole_pin_wrong_order_raises(self):
        with pytest.raises(ValueError):
            ConnectorPair(stud=self._hole(), anti_stud=self._pin())

    def test_axle_axle_hole_pair_valid(self):
        axle = Connector("axle", ConnectorType.TECHNIC_AXLE, Point3D(0, 12, 10), Vector3D(1, 0, 0))
        axle_hole = Connector("ah", ConnectorType.TECHNIC_AXLE_HOLE, Point3D(0, 12, 10), Vector3D(1, 0, 0))
        pair = ConnectorPair(stud=axle, anti_stud=axle_hole)
        assert pair.stud.connector_type == ConnectorType.TECHNIC_AXLE


# ---------------------------------------------------------------------------
# Compatibility matrix
# ---------------------------------------------------------------------------

class TestCompatibility:
    def test_stud_anti_stud_compatible(self):
        assert types_are_compatible(ConnectorType.STUD, ConnectorType.ANTI_STUD)
        assert types_are_compatible(ConnectorType.ANTI_STUD, ConnectorType.STUD)

    def test_pin_hole_compatible(self):
        assert types_are_compatible(ConnectorType.TECHNIC_PIN, ConnectorType.TECHNIC_HOLE)
        assert types_are_compatible(ConnectorType.TECHNIC_HOLE, ConnectorType.TECHNIC_PIN)

    def test_axle_axle_hole_compatible(self):
        assert types_are_compatible(ConnectorType.TECHNIC_AXLE, ConnectorType.TECHNIC_AXLE_HOLE)
        assert types_are_compatible(ConnectorType.TECHNIC_AXLE_HOLE, ConnectorType.TECHNIC_AXLE)

    def test_stud_hole_incompatible(self):
        assert not types_are_compatible(ConnectorType.STUD, ConnectorType.TECHNIC_HOLE)

    def test_pin_anti_stud_incompatible(self):
        assert not types_are_compatible(ConnectorType.TECHNIC_PIN, ConnectorType.ANTI_STUD)

    def test_pin_axle_incompatible(self):
        assert not types_are_compatible(ConnectorType.TECHNIC_PIN, ConnectorType.TECHNIC_AXLE)

    def test_stud_stud_incompatible(self):
        assert not types_are_compatible(ConnectorType.STUD, ConnectorType.STUD)

    def test_is_technic_pair(self):
        assert _is_technic_pair(ConnectorType.TECHNIC_PIN, ConnectorType.TECHNIC_HOLE)
        assert not _is_technic_pair(ConnectorType.STUD, ConnectorType.TECHNIC_HOLE)


# ---------------------------------------------------------------------------
# Connection rules — Technic normal orientation
# ---------------------------------------------------------------------------

class TestTechnicRules:
    rules = DEFAULT_RULES

    def _make_pin(self, nx, ny, nz):
        return Connector("pin", ConnectorType.TECHNIC_PIN,
                         Point3D(0, 12, 10), Vector3D(nx, ny, nz))

    def _make_hole(self, nx, ny, nz):
        return Connector("hole", ConnectorType.TECHNIC_HOLE,
                         Point3D(0, 12, 10), Vector3D(nx, ny, nz))

    def test_parallel_normals_valid(self):
        """Pin and hole both pointing +X: co-axial → valid."""
        pin = self._make_pin(1, 0, 0)
        hole = self._make_hole(1, 0, 0)
        result = self.rules.check_normal_orientation(pin, hole)
        assert result.valid

    def test_anti_parallel_normals_valid(self):
        """Pin pointing +X, hole pointing -X: anti-parallel but co-axial → valid."""
        pin = self._make_pin(1, 0, 0)
        hole = self._make_hole(-1, 0, 0)
        result = self.rules.check_normal_orientation(pin, hole)
        assert result.valid

    def test_perpendicular_normals_invalid(self):
        """Pin pointing +X, hole pointing +Z: perpendicular → invalid."""
        pin = self._make_pin(1, 0, 0)
        hole = self._make_hole(0, 0, 1)
        result = self.rules.check_normal_orientation(pin, hole)
        assert not result.valid

    def test_standard_stud_anti_stud_still_antiparallel(self):
        """Regression: standard stud/anti-stud rules unchanged."""
        stud = Connector("s", ConnectorType.STUD,
                         Point3D(10, 24, 10), Vector3D(0, 1, 0))
        anti = Connector("a", ConnectorType.ANTI_STUD,
                         Point3D(10, 24, 10), Vector3D(0, -1, 0))
        result = self.rules.check_normal_orientation(stud, anti)
        assert result.valid

    def test_full_validate_technic_pin_hole_aligned(self):
        """Full validate() for a pin-hole pair that is aligned and co-axial."""
        pin = Connector("pin", ConnectorType.TECHNIC_PIN,
                        Point3D(0, 12, 10), Vector3D(1, 0, 0))
        hole = Connector("hole", ConnectorType.TECHNIC_HOLE,
                         Point3D(0, 12, 10), Vector3D(1, 0, 0))
        result = self.rules.validate(pin, hole)
        assert result.valid

    def test_full_validate_technic_wrong_type_fails(self):
        pin = Connector("pin", ConnectorType.TECHNIC_PIN,
                        Point3D(0, 12, 10), Vector3D(1, 0, 0))
        anti = Connector("anti", ConnectorType.ANTI_STUD,
                         Point3D(0, 12, 10), Vector3D(0, -1, 0))
        result = self.rules.validate(pin, anti)
        assert not result.valid

    def test_connection_score_technic_aligned_is_high(self):
        pin = Connector("pin", ConnectorType.TECHNIC_PIN,
                        Point3D(0, 12, 10), Vector3D(1, 0, 0))
        hole = Connector("hole", ConnectorType.TECHNIC_HOLE,
                         Point3D(0, 12, 10), Vector3D(1, 0, 0))
        score = self.rules.connection_score(pin, hole)
        assert score == pytest.approx(1.0)

    def test_form_connection_technic(self):
        pin = Connector("pin", ConnectorType.TECHNIC_PIN,
                        Point3D(0, 12, 10), Vector3D(1, 0, 0))
        hole = Connector("hole", ConnectorType.TECHNIC_HOLE,
                         Point3D(0, 12, 10), Vector3D(1, 0, 0))
        pair = self.rules.form_connection(pin, hole)
        assert pair.stud.connector_type == ConnectorType.TECHNIC_PIN
        assert pair.anti_stud.connector_type == ConnectorType.TECHNIC_HOLE
        assert not pin.is_free
        assert not hole.is_free


# ---------------------------------------------------------------------------
# Technic part metadata
# ---------------------------------------------------------------------------

class TestTechnicMetadata:
    def test_all_technic_have_technic_category(self):
        for part in ALL_TECHNIC.values():
            assert part.category == PartCategory.TECHNIC

    def test_all_technic_have_technic_geometry(self):
        for part in ALL_TECHNIC.values():
            assert part.technic_geometry is not None

    def test_1x2_has_2_holes(self):
        tg = TECHNIC_BRICK_1x2.technic_geometry
        assert len(tg.hole_positions) == 2

    def test_1x4_has_4_holes(self):
        tg = TECHNIC_BRICK_1x4.technic_geometry
        assert len(tg.hole_positions) == 4

    def test_1x2_height_is_brick_height(self):
        assert TECHNIC_BRICK_1x2.dimensions.height_ldu == pytest.approx(BRICK_HEIGHT_LDU)

    def test_get_technic_valid(self):
        p = get_technic_part("technic_brick_1x2")
        assert p.part_id == "technic_brick_1x2"

    def test_get_technic_invalid_raises(self):
        with pytest.raises(KeyError):
            get_technic_part("nope")

    def test_serialisation_roundtrip(self):
        d = TECHNIC_BRICK_1x4.to_dict()
        assert "technic_geometry" in d
        restored = type(TECHNIC_BRICK_1x4).from_dict(d)
        assert restored.technic_geometry == TECHNIC_BRICK_1x4.technic_geometry
        assert restored.category == PartCategory.TECHNIC


# ---------------------------------------------------------------------------
# Technic connector generation
# ---------------------------------------------------------------------------

class TestTechnicConnectorGeneration:
    def test_1x2_has_studs(self):
        conns = generate_connectors(TECHNIC_BRICK_1x2, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert len(studs) == 2

    def test_1x2_has_anti_studs(self):
        conns = generate_connectors(TECHNIC_BRICK_1x2, Pose.identity())
        anti = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        assert len(anti) == 2

    def test_1x2_has_four_technic_holes(self):
        """2 hole positions × 2 openings (pos + neg) = 4 TECHNIC_HOLE connectors."""
        conns = generate_connectors(TECHNIC_BRICK_1x2, Pose.identity())
        holes = [c for c in conns if c.connector_type == ConnectorType.TECHNIC_HOLE]
        assert len(holes) == 4

    def test_1x4_has_eight_technic_holes(self):
        conns = generate_connectors(TECHNIC_BRICK_1x4, Pose.identity())
        holes = [c for c in conns if c.connector_type == ConnectorType.TECHNIC_HOLE]
        assert len(holes) == 8

    def test_holes_at_mid_height(self):
        """TECHNIC_HOLE connectors sit at the vertical centre of the brick."""
        conns = generate_connectors(TECHNIC_BRICK_1x2, Pose.identity())
        holes = [c for c in conns if c.connector_type == ConnectorType.TECHNIC_HOLE]
        expected_y = BRICK_HEIGHT_LDU / 2.0
        for h in holes:
            assert h.position.y == pytest.approx(expected_y)

    def test_holes_normal_along_x(self):
        """Default hole_axis='x' → normals point ±X."""
        conns = generate_connectors(TECHNIC_BRICK_1x2, Pose.identity())
        holes = [c for c in conns if c.connector_type == ConnectorType.TECHNIC_HOLE]
        for h in holes:
            assert h.normal.y == pytest.approx(0.0)
            assert h.normal.z == pytest.approx(0.0)
            assert abs(h.normal.x) == pytest.approx(1.0)

    def test_unique_connector_ids(self):
        conns = generate_connectors(TECHNIC_BRICK_1x4, Pose.identity())
        ids = [c.connector_id for c in conns]
        assert len(ids) == len(set(ids))

    def test_stud_normal_up(self):
        conns = generate_connectors(TECHNIC_BRICK_1x2, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        for s in studs:
            assert s.normal.y == pytest.approx(1.0)

    def test_anti_stud_normal_down(self):
        conns = generate_connectors(TECHNIC_BRICK_1x2, Pose.identity())
        anti = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        for a in anti:
            assert a.normal.y == pytest.approx(-1.0)
