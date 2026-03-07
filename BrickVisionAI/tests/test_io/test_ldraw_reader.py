"""Tests for Phase C LDraw reader."""

import pytest
from brick_geometry.io.ldraw_reader import (
    LDrawReader,
    LDrawRecord,
    LDrawParseResult,
    _ldraw_to_engine_pos,
    _ldraw_to_engine_matrix,
    _parse_rotation,
)
from brick_geometry.core.geometry import Point3D
from brick_geometry.core.transforms import Rotation, Pose
from brick_geometry.core.constants import BRICK_HEIGHT_LDU, STUD_SPACING_LDU
from brick_geometry.parts.part_catalog import PartCatalog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def reader():
    return LDrawReader()


@pytest.fixture
def catalog():
    return PartCatalog.default()


# ---------------------------------------------------------------------------
# Y-axis conversion helpers
# ---------------------------------------------------------------------------

class TestYConversion:
    def test_ldraw_to_engine_pos_flips_y(self):
        p = _ldraw_to_engine_pos(10.0, -24.0, 5.0)
        assert p.x == pytest.approx(10.0)
        assert p.y == pytest.approx(24.0)   # −(−24) = 24
        assert p.z == pytest.approx(5.0)

    def test_ldraw_to_engine_pos_zero(self):
        p = _ldraw_to_engine_pos(0.0, 0.0, 0.0)
        assert p == Point3D(0.0, 0.0, 0.0)

    def test_ldraw_to_engine_matrix_identity(self):
        m = _ldraw_to_engine_matrix(1, 0, 0, 0, 1, 0, 0, 0, 1)
        assert m == (1, 0, 0, 0, 1, 0, 0, 0, 1)

    def test_ldraw_to_engine_matrix_negates_correct_elements(self):
        # Row 1 and col 1 should be negated
        # Original: (a,b,c, d,e,f, g,h,i)
        # Result:   (a,-b,c, -d,e,-f, g,-h,i)
        m = _ldraw_to_engine_matrix(1, 2, 3, 4, 5, 6, 7, 8, 9)
        assert m == (1, -2, 3, -4, 5, -6, 7, -8, 9)

    def test_roundtrip_y_identity(self):
        """Applying the Y-flip twice returns identity."""
        m = (1, 0, 0, 0, 1, 0, 0, 0, 1)
        m2 = _ldraw_to_engine_matrix(*m)
        m3 = _ldraw_to_engine_matrix(*m2)
        assert m3 == m


# ---------------------------------------------------------------------------
# Rotation matrix validation
# ---------------------------------------------------------------------------

class TestParseRotation:
    def _errors(self):
        return []

    def test_identity_valid(self):
        errors = []
        rot = _parse_rotation([1,0,0, 0,1,0, 0,0,1], 1, errors)
        assert rot is not None
        assert errors == []

    def test_non_90_deg_returns_none_and_error(self):
        import math
        angle = math.radians(45)
        errors = []
        rot = _parse_rotation(
            [math.cos(angle), -math.sin(angle), 0,
             math.sin(angle),  math.cos(angle), 0,
             0, 0, 1],
            1, errors
        )
        assert rot is None
        assert len(errors) == 1

    def test_90_y_rotation_valid(self):
        errors = []
        rot = _parse_rotation([0, 0, 1,  0, 1, 0,  -1, 0, 0], 1, errors)
        assert rot is not None
        assert errors == []

    def test_bad_row_returns_none(self):
        # Row 0 has two non-zero entries
        errors = []
        rot = _parse_rotation([1, 1, 0,  0, 1, 0,  0, 0, 1], 1, errors)
        assert rot is None
        assert len(errors) > 0

    def test_bad_column_returns_none(self):
        errors = []
        rot = _parse_rotation([1, 0, 0,  1, 0, 0,  0, 0, 1], 1, errors)
        assert rot is None
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Parsing type-1 lines
# ---------------------------------------------------------------------------

SIMPLE_LDR = """\
0 Test Model
0 Name: test.ldr
0 Author: Tester
1 16 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat
1 4 0 -24 0 1 0 0 0 1 0 0 0 1 3001.dat
0 STEP
"""


class TestReadString:
    def test_record_count(self, reader):
        result = reader.read_string(SIMPLE_LDR)
        assert len(result.records) == 2

    def test_title_parsed(self, reader):
        result = reader.read_string(SIMPLE_LDR)
        assert result.title == "Test Model"

    def test_author_parsed(self, reader):
        result = reader.read_string(SIMPLE_LDR)
        assert result.author == "Tester"

    def test_colour_codes(self, reader):
        result = reader.read_string(SIMPLE_LDR)
        assert result.records[0].colour == 16
        assert result.records[1].colour == 4

    def test_y_flip_applied_to_position(self, reader):
        """LDraw y=-24 → engine y=+24."""
        result = reader.read_string(SIMPLE_LDR)
        r0 = result.records[0]
        r1 = result.records[1]
        assert r0.pose.position.y == pytest.approx(0.0)
        assert r1.pose.position.y == pytest.approx(24.0)

    def test_identity_rotation_parsed(self, reader):
        result = reader.read_string(SIMPLE_LDR)
        assert result.records[0].pose.rotation == Rotation.identity()

    def test_filename_stored(self, reader):
        result = reader.read_string(SIMPLE_LDR)
        assert result.records[0].ldraw_filename == "3001.dat"

    def test_step_zero_initially(self, reader):
        result = reader.read_string(SIMPLE_LDR)
        # Both records appear before the first STEP increment
        assert result.records[0].step == 0
        assert result.records[1].step == 0

    def test_no_catalog_part_is_none(self, reader):
        result = reader.read_string(SIMPLE_LDR, catalog=None)
        assert all(r.part is None for r in result.records)

    def test_empty_string(self, reader):
        result = reader.read_string("")
        assert result.records == []

    def test_only_comments(self, reader):
        result = reader.read_string("0 hello\n0 world\n")
        assert result.records == []


class TestCatalogLookup:
    def test_known_ldraw_id_resolves(self, reader, catalog):
        ldr = "1 16 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat\n"
        result = reader.read_string(ldr, catalog=catalog)
        assert result.records[0].part is not None
        assert result.records[0].part.ldraw_id == "3001"

    def test_unknown_part_is_none_with_warning(self, reader, catalog):
        ldr = "1 16 0 0 0 1 0 0 0 1 0 0 0 1 UNKNOWN_PART.dat\n"
        result = reader.read_string(ldr, catalog=catalog)
        assert result.records[0].part is None
        assert any("UNKNOWN_PART" in w for w in result.warnings)


class TestMalformedLines:
    def test_too_few_tokens_produces_error(self, reader):
        ldr = "1 16 0 0 0\n"  # only 5 tokens after "1"
        result = reader.read_string(ldr)
        assert len(result.errors) > 0
        assert len(result.records) == 0

    def test_non_numeric_position_produces_error(self, reader):
        ldr = "1 16 X Y Z 1 0 0 0 1 0 0 0 1 3001.dat\n"
        result = reader.read_string(ldr)
        assert len(result.errors) > 0

    def test_non_90deg_matrix_falls_back_to_identity(self, reader):
        import math
        a = math.cos(math.radians(45))
        s = math.sin(math.radians(45))
        ldr = (
            f"1 16 0 0 0 {a:.4f} {-s:.4f} 0 "
            f"{s:.4f} {a:.4f} 0 0 0 1 3001.dat\n"
        )
        result = reader.read_string(ldr)
        assert len(result.records) == 1
        assert result.records[0].pose.rotation == Rotation.identity()
        assert len(result.errors) > 0


class TestMultiStep:
    MULTI_STEP = """\
1 16 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat
0 STEP
1 16 0 -24 0 1 0 0 0 1 0 0 0 1 3001.dat
0 STEP
1 16 0 -48 0 1 0 0 0 1 0 0 0 1 3001.dat
"""

    def test_step_indices(self, reader):
        result = reader.read_string(self.MULTI_STEP)
        assert result.records[0].step == 0
        assert result.records[1].step == 1
        assert result.records[2].step == 2

    def test_three_records(self, reader):
        result = reader.read_string(self.MULTI_STEP)
        assert len(result.records) == 3

    def test_y_positions_across_steps(self, reader):
        result = reader.read_string(self.MULTI_STEP)
        ys = [r.pose.position.y for r in result.records]
        assert ys == pytest.approx([0.0, 24.0, 48.0])


class TestReadFile:
    def test_read_file_roundtrip(self, reader, tmp_path, catalog):
        """Write an LDR file manually and read it back."""
        content = (
            "0 File Test\n"
            "0 Author: Test\n"
            "1 16 0 0 0 1 0 0 0 1 0 0 0 1 3001.dat\n"
        )
        p = tmp_path / "test.ldr"
        p.write_text(content, encoding="utf-8")
        result = reader.read_file(p, catalog=catalog)
        assert len(result.records) == 1
        assert result.records[0].part is not None
