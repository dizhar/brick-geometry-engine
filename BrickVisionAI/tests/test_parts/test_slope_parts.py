"""Tests for Phase B slope part metadata and connector generation."""

import pytest
from brick_geometry.parts.part_metadata import PartCategory, SlopeGeometry
from brick_geometry.parts.slope_parts import (
    ALL_SLOPES,
    SLOPE_1x1_STEEP,
    SLOPE_1x2_45,
    SLOPE_1x2_30,
    SLOPE_2x2_45,
    SLOPE_2x4_18,
    get_slope,
)
from brick_geometry.core.transforms import Pose
from brick_geometry.core.constants import BRICK_HEIGHT_LDU, PLATE_HEIGHT_LDU, STUD_SPACING_LDU
from brick_geometry.connectors.connector_model import ConnectorType
from brick_geometry.assembly.assembly_node import generate_connectors


# ---------------------------------------------------------------------------
# Metadata / SlopeGeometry
# ---------------------------------------------------------------------------

class TestSlopeMetadata:
    def test_all_slopes_have_slope_category(self):
        for part in ALL_SLOPES.values():
            assert part.category == PartCategory.SLOPE

    def test_all_slopes_have_slope_geometry(self):
        for part in ALL_SLOPES.values():
            assert part.slope_geometry is not None

    def test_height_high_matches_dimensions(self):
        """height_high_ldu must equal dimensions.height_ldu for correct AABBs."""
        for part in ALL_SLOPES.values():
            sg = part.slope_geometry
            assert sg.height_high_ldu == pytest.approx(part.dimensions.height_ldu)

    def test_height_low_lte_high(self):
        for part in ALL_SLOPES.values():
            sg = part.slope_geometry
            assert sg.height_low_ldu <= sg.height_high_ldu

    def test_slope_1x1_steep_no_top_stud(self):
        assert SLOPE_1x1_STEEP.slope_geometry.flat_rows_at_high_end == 0

    def test_slope_1x2_45_has_one_flat_row(self):
        assert SLOPE_1x2_45.slope_geometry.flat_rows_at_high_end == 1

    def test_slope_2x4_18_has_two_flat_rows(self):
        assert SLOPE_2x4_18.slope_geometry.flat_rows_at_high_end == 2

    def test_get_slope_valid(self):
        s = get_slope("slope_1x2_45")
        assert s.part_id == "slope_1x2_45"

    def test_get_slope_invalid_raises(self):
        with pytest.raises(KeyError, match="nonexistent"):
            get_slope("nonexistent")

    def test_slope_geometry_delta_height(self):
        sg = SLOPE_1x2_45.slope_geometry
        assert sg.delta_height_ldu == pytest.approx(BRICK_HEIGHT_LDU)  # 0 → 24

    def test_slope_serialisation_roundtrip(self):
        d = SLOPE_2x2_45.to_dict()
        assert "slope_geometry" in d
        restored = type(SLOPE_2x2_45).from_dict(d)
        assert restored.slope_geometry == SLOPE_2x2_45.slope_geometry
        assert restored.category == PartCategory.SLOPE


# ---------------------------------------------------------------------------
# Slope connector generation
# ---------------------------------------------------------------------------

class TestSlopeConnectors:
    def test_1x1_steep_has_no_studs(self):
        """flat_rows_at_high_end=0 → no studs on top."""
        conns = generate_connectors(SLOPE_1x1_STEEP, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert studs == []

    def test_1x1_steep_has_one_anti_stud(self):
        conns = generate_connectors(SLOPE_1x1_STEEP, Pose.identity())
        anti_studs = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        assert len(anti_studs) == 1

    def test_1x2_45_has_one_stud(self):
        """flat_rows_at_high_end=1 on a 1×2 slope → 1 stud at back row."""
        conns = generate_connectors(SLOPE_1x2_45, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert len(studs) == 1

    def test_1x2_45_has_two_anti_studs(self):
        conns = generate_connectors(SLOPE_1x2_45, Pose.identity())
        anti_studs = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        assert len(anti_studs) == 2

    def test_2x2_45_has_two_studs(self):
        """flat_rows_at_high_end=1 on a 2×2 slope → 2 studs at back row."""
        conns = generate_connectors(SLOPE_2x2_45, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert len(studs) == 2

    def test_2x2_45_has_four_anti_studs(self):
        conns = generate_connectors(SLOPE_2x2_45, Pose.identity())
        anti_studs = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        assert len(anti_studs) == 4

    def test_2x4_18_has_four_studs(self):
        """flat_rows_at_high_end=2 on a 2×4 slope → 2×2=4 studs."""
        conns = generate_connectors(SLOPE_2x4_18, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert len(studs) == 4

    def test_stud_at_high_end_z(self):
        """Stud on 1×2 slope should be at the back (high-Z) row."""
        conns = generate_connectors(SLOPE_1x2_45, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert len(studs) == 1
        expected_z = 1.5 * STUD_SPACING_LDU   # row 1 (0-indexed), centred
        assert studs[0].position.z == pytest.approx(expected_z)

    def test_stud_height_at_high_end(self):
        """Stud y-position should be at height_ldu (24 for a brick-height slope)."""
        conns = generate_connectors(SLOPE_1x2_45, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert studs[0].position.y == pytest.approx(BRICK_HEIGHT_LDU)

    def test_anti_stud_at_y_zero(self):
        conns = generate_connectors(SLOPE_1x2_45, Pose.identity())
        anti_studs = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        for a in anti_studs:
            assert a.position.y == pytest.approx(0.0)

    def test_stud_normal_up(self):
        conns = generate_connectors(SLOPE_1x2_45, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        for s in studs:
            assert s.normal.y == pytest.approx(1.0)

    def test_anti_stud_normal_down(self):
        conns = generate_connectors(SLOPE_1x2_45, Pose.identity())
        anti = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        for a in anti:
            assert a.normal.y == pytest.approx(-1.0)

    def test_unique_connector_ids(self):
        conns = generate_connectors(SLOPE_2x4_18, Pose.identity())
        ids = [c.connector_id for c in conns]
        assert len(ids) == len(set(ids))
