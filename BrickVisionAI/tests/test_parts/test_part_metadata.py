import pytest
from brick_geometry.parts.part_metadata import (
    PartCategory, PartDimensions, PartMetadata, make_brick, make_plate
)
from brick_geometry.core.constants import BRICK_HEIGHT_LDU, PLATE_HEIGHT_LDU, STUD_SPACING_LDU


class TestPartDimensions:
    def test_width_ldu(self):
        dims = PartDimensions(studs_x=2, studs_z=4, height_ldu=24)
        assert dims.width_ldu == 2 * STUD_SPACING_LDU

    def test_depth_ldu(self):
        dims = PartDimensions(studs_x=2, studs_z=4, height_ldu=24)
        assert dims.depth_ldu == 4 * STUD_SPACING_LDU

    def test_bounding_box_origin(self):
        dims = PartDimensions(studs_x=2, studs_z=4, height_ldu=24)
        bb = dims.bounding_box()
        assert bb.min_point.x == 0
        assert bb.min_point.y == 0
        assert bb.min_point.z == 0

    def test_bounding_box_max(self):
        dims = PartDimensions(studs_x=2, studs_z=4, height_ldu=24)
        bb = dims.bounding_box()
        assert bb.max_point.x == 2 * STUD_SPACING_LDU
        assert bb.max_point.y == 24
        assert bb.max_point.z == 4 * STUD_SPACING_LDU


class TestMakeBrick:
    def test_make_brick_category(self):
        b = make_brick("test_1x1", "Test 1x1", 1, 1)
        assert b.category == PartCategory.BRICK

    def test_make_brick_height(self):
        b = make_brick("test_2x4", "Test 2x4", 2, 4)
        assert b.dimensions.height_ldu == BRICK_HEIGHT_LDU

    def test_make_plate_category(self):
        p = make_plate("test_plate", "Test plate", 2, 2)
        assert p.category == PartCategory.PLATE

    def test_make_plate_height(self):
        p = make_plate("test_plate", "Test plate", 2, 2)
        assert p.dimensions.height_ldu == PLATE_HEIGHT_LDU


class TestPartMetadataSerialization:
    def test_round_trip_dict(self):
        original = make_brick("brick_2x4", "Brick 2x4", 2, 4, ldraw_id="3001")
        d = original.to_dict()
        restored = PartMetadata.from_dict(d)
        assert restored.part_id == original.part_id
        assert restored.name == original.name
        assert restored.category == original.category
        assert restored.dimensions.studs_x == original.dimensions.studs_x
        assert restored.dimensions.studs_z == original.dimensions.studs_z
        assert restored.dimensions.height_ldu == original.dimensions.height_ldu
        assert restored.ldraw_id == original.ldraw_id

    def test_footprint(self):
        b = make_brick("b", "b", 2, 4)
        assert b.footprint == (2, 4)

    def test_bounding_box_matches_dimensions(self):
        b = make_brick("b", "b", 2, 4)
        bb = b.bounding_box()
        assert bb.max_point.x == b.dimensions.width_ldu
        assert bb.max_point.z == b.dimensions.depth_ldu
