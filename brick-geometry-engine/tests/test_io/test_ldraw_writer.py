"""Tests for Phase C LDraw writer."""

import pytest
from brick_geometry.io.ldraw_writer import (
    LDrawWriter,
    _engine_to_ldraw_pos,
    _engine_to_ldraw_matrix,
)
from brick_geometry.core.geometry import Point3D
from brick_geometry.core.transforms import Rotation, Pose
from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.parts.part_catalog import PartCatalog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pose(x=0.0, y=0.0, z=0.0) -> Pose:
    return Pose(position=Point3D(x, y, z), rotation=Rotation.identity())


def _single_brick_assembly(name="test") -> Assembly:
    catalog = PartCatalog.default()
    part = catalog.get("brick_2x4")
    assembly = Assembly(name=name)
    assembly.place_part(part, _pose(), check_collision=False)
    return assembly


# ---------------------------------------------------------------------------
# Y-axis conversion helpers (writer side)
# ---------------------------------------------------------------------------

class TestEngineToLDrawPos:
    def test_y_negated(self):
        pose = _pose(10.0, 24.0, 5.0)
        lx, ly, lz = _engine_to_ldraw_pos(pose)
        assert lx == pytest.approx(10.0)
        assert ly == pytest.approx(-24.0)
        assert lz == pytest.approx(5.0)

    def test_zero_unchanged(self):
        pose = _pose(0.0, 0.0, 0.0)
        assert _engine_to_ldraw_pos(pose) == (0.0, 0.0, 0.0)

    def test_negative_y_becomes_positive(self):
        pose = _pose(0.0, -8.0, 0.0)
        _, ly, _ = _engine_to_ldraw_pos(pose)
        assert ly == pytest.approx(8.0)


class TestEngineToLDrawMatrix:
    def test_identity_unchanged(self):
        pose = Pose(Point3D(0, 0, 0), Rotation.identity())
        m = _engine_to_ldraw_matrix(pose)
        assert m == (1, 0, 0, 0, 1, 0, 0, 0, 1)

    def test_negates_correct_elements(self):
        # Same formula as reader: (a,-b,c, -d,e,-f, g,-h,i)
        rot = Rotation((1, 2, 3, 4, 5, 6, 7, 8, 9))
        pose = Pose(Point3D(0, 0, 0), rot)
        m = _engine_to_ldraw_matrix(pose)
        assert m == (1, -2, 3, -4, 5, -6, 7, -8, 9)

    def test_roundtrip_with_reader_matrix(self):
        """Reader and writer Y-flip are inverses: apply both → identity."""
        from brick_geometry.io.ldraw_reader import _ldraw_to_engine_matrix
        engine_mat = _ldraw_to_engine_matrix(1, 0, 0, 0, 1, 0, 0, 0, 1)
        pose = Pose(Point3D(0, 0, 0), Rotation(engine_mat))
        ldraw_mat = _engine_to_ldraw_matrix(pose)
        assert ldraw_mat == (1, 0, 0, 0, 1, 0, 0, 0, 1)


# ---------------------------------------------------------------------------
# Header / footer structure
# ---------------------------------------------------------------------------

class TestHeader:
    def test_title_in_first_line(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm, title="My Model")
        lines = content.splitlines()
        assert lines[0] == "0 My Model"

    def test_name_line(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm, title="My Model")
        lines = content.splitlines()
        assert any(l.startswith("0 Name:") for l in lines)

    def test_author_line_present_when_given(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm, author="Test Author")
        assert "0 Author: Test Author" in content

    def test_no_author_line_when_empty(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm, title="T", author="")
        assert "0 Author:" not in content

    def test_license_line(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        assert "0 !LICENSE" in content

    def test_footer_step(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        assert "0 STEP" in content

    def test_footer_nofile(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        assert "0 NOFILE" in content

    def test_crlf_line_endings(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        assert "\r\n" in content


# ---------------------------------------------------------------------------
# Type-1 lines
# ---------------------------------------------------------------------------

class TestType1Lines:
    def _type1_lines(self, content: str):
        return [l for l in content.splitlines() if l.startswith("1 ")]

    def test_one_line_per_node(self):
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="t")
        asm.place_part(part, _pose(0, 0, 0), check_collision=False)
        asm.place_part(part, _pose(0, 0, 100), check_collision=False)
        writer = LDrawWriter()
        content = writer.write_assembly(asm)
        assert len(self._type1_lines(content)) == 2

    def test_type1_prefix(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        t1 = self._type1_lines(content)
        assert len(t1) == 1
        assert t1[0].startswith("1 ")

    def test_default_colour(self):
        writer = LDrawWriter(default_colour=4)
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        t1 = self._type1_lines(content)[0]
        tokens = t1.split()
        assert tokens[1] == "4"

    def test_colour_map_override(self):
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="t")
        node = asm.place_part(part, _pose(), check_collision=False)
        writer = LDrawWriter()
        content = writer.write_assembly(asm, colour_map={node.instance_id: 14})
        t1 = self._type1_lines(content)[0]
        assert t1.split()[1] == "14"

    def test_y_position_flipped(self):
        """Engine y=24 → LDraw y=-24."""
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="t")
        asm.place_part(part, _pose(0, 24, 0), check_collision=False)
        writer = LDrawWriter()
        content = writer.write_assembly(asm)
        t1 = self._type1_lines(content)[0]
        tokens = t1.split()
        # tokens: 1 colour x y z a b c d e f g h i filename
        assert tokens[3] == "-24"  # y position

    def test_identity_matrix_in_line(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        t1 = self._type1_lines(content)[0]
        tokens = t1.split()
        # matrix starts at token index 5, 9 values
        mat = [int(v) for v in tokens[5:14]]
        assert mat == [1, 0, 0, 0, 1, 0, 0, 0, 1]

    def test_filename_uses_ldraw_id(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        t1 = self._type1_lines(content)[0]
        # brick_2x4 has ldraw_id "3001"
        assert t1.endswith("3001.dat")

    def test_filename_fallback_to_part_id(self):
        """Parts without ldraw_id should use part_id as filename."""
        from brick_geometry.parts.part_metadata import make_brick
        custom = make_brick("custom_part", "Custom", studs_x=2, studs_z=4, ldraw_id=None)
        asm = Assembly(name="t")
        asm.place_part(custom, _pose(), check_collision=False)
        writer = LDrawWriter()
        content = writer.write_assembly(asm)
        t1 = self._type1_lines(content)[0]
        assert t1.endswith("custom_part.dat")

    def test_integer_positions_no_decimal(self):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        content = writer.write_assembly(asm)
        t1 = self._type1_lines(content)[0]
        tokens = t1.split()
        # x, y, z at indices 2, 3, 4 should be integer strings
        for tok in tokens[2:5]:
            assert "." not in tok


# ---------------------------------------------------------------------------
# write_file round-trip
# ---------------------------------------------------------------------------

class TestWriteFile:
    def test_file_is_created(self, tmp_path):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        p = tmp_path / "out.ldr"
        writer.write_file(asm, p)
        assert p.exists()

    def test_file_content_matches_write_assembly(self, tmp_path):
        writer = LDrawWriter()
        asm = _single_brick_assembly()
        expected = writer.write_assembly(asm, title="T", author="A")
        p = tmp_path / "out.ldr"
        writer.write_file(asm, p, title="T", author="A")
        # Read with newline="" to preserve CRLF as written
        assert p.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n") == expected.replace("\r\n", "\n")

    def test_reader_writer_roundtrip(self, tmp_path):
        """Write with writer, read back with reader — records match."""
        from brick_geometry.io.ldraw_reader import LDrawReader
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="rt")
        asm.place_part(part, _pose(0, 0, 0), check_collision=False)
        asm.place_part(part, _pose(0, 0, 100), check_collision=False)

        writer = LDrawWriter()
        p = tmp_path / "rt.ldr"
        writer.write_file(asm, p, title="Roundtrip")

        reader = LDrawReader()
        result = reader.read_file(p, catalog=catalog)
        assert len(result.records) == 2
        assert result.title == "Roundtrip"
        zs = sorted(r.pose.position.z for r in result.records)
        assert zs == pytest.approx([0.0, 100.0])
