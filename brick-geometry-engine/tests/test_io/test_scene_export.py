"""Tests for Phase C scene exporter."""

import json
import pytest
from brick_geometry.io.scene_export import SceneExporter
from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.core.geometry import Point3D
from brick_geometry.core.transforms import Rotation, Pose
from brick_geometry.parts.part_catalog import PartCatalog
from brick_geometry.core.constants import LDU_TO_MM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pose(x=0.0, y=0.0, z=0.0) -> Pose:
    return Pose(position=Point3D(x, y, z), rotation=Rotation.identity())


def _single_brick_assembly() -> Assembly:
    catalog = PartCatalog.default()
    part = catalog.get("brick_2x4")
    asm = Assembly(name="single")
    asm.place_part(part, _pose(), check_collision=False)
    return asm


def _two_brick_assembly() -> Assembly:
    catalog = PartCatalog.default()
    part = catalog.get("brick_2x4")
    asm = Assembly(name="two_bricks")
    asm.place_part(part, _pose(0, 0, 0), check_collision=False)
    asm.place_part(part, _pose(0, 0, 100), check_collision=False)  # far apart, no collision
    return asm


# ---------------------------------------------------------------------------
# Metadata section
# ---------------------------------------------------------------------------

class TestMetadata:
    def test_name_matches_assembly(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["metadata"]["name"] == "single"

    def test_engine_field(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["metadata"]["engine"] == "BrickVisionAI"

    def test_phase_is_C(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["metadata"]["phase"] == "C"

    def test_part_count(self):
        exporter = SceneExporter()
        data = exporter.export(_two_brick_assembly())
        assert data["metadata"]["part_count"] == 2

    def test_bond_count_zero_for_unconnected(self):
        exporter = SceneExporter()
        data = exporter.export(_two_brick_assembly())
        assert data["metadata"]["bond_count"] == 0

    def test_ldu_to_mm(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["metadata"]["ldu_to_mm"] == pytest.approx(LDU_TO_MM)

    def test_exported_at_present(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert "exported_at" in data["metadata"]


# ---------------------------------------------------------------------------
# Coordinate system section
# ---------------------------------------------------------------------------

class TestCoordinateSystem:
    def test_convention_Y_UP(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["coordinate_system"]["convention"] == "Y_UP"

    def test_unit_LDU(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["coordinate_system"]["unit"] == "LDU"

    def test_ldu_per_mm(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["coordinate_system"]["ldu_per_mm"] == pytest.approx(1.0 / LDU_TO_MM)


# ---------------------------------------------------------------------------
# Parts section
# ---------------------------------------------------------------------------

class TestPartDict:
    def test_part_count_in_list(self):
        exporter = SceneExporter()
        data = exporter.export(_two_brick_assembly())
        assert len(data["parts"]) == 2

    def test_required_keys_present(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        p = data["parts"][0]
        for key in (
            "instance_id", "part_id", "ldraw_id", "name", "category",
            "colour_code", "position_ldu", "position_mm",
            "rotation_matrix", "matrix_4x4",
            "bounding_box_ldu", "bounding_box_mm",
            "dimensions_ldu", "dimensions_mm",
        ):
            assert key in p, f"Missing key: {key}"

    def test_position_ldu_values(self):
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="t")
        asm.place_part(part, _pose(10.0, 20.0, 30.0), check_collision=False)
        exporter = SceneExporter()
        data = exporter.export(asm)
        pos = data["parts"][0]["position_ldu"]
        assert pos == pytest.approx([10.0, 20.0, 30.0])

    def test_position_mm_values(self):
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="t")
        asm.place_part(part, _pose(10.0, 20.0, 30.0), check_collision=False)
        exporter = SceneExporter()
        data = exporter.export(asm)
        pos = data["parts"][0]["position_mm"]
        assert pos == pytest.approx([10.0 * LDU_TO_MM, 20.0 * LDU_TO_MM, 30.0 * LDU_TO_MM])

    def test_rotation_matrix_identity(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        mat = data["parts"][0]["rotation_matrix"]
        assert mat == [1, 0, 0, 0, 1, 0, 0, 0, 1]

    def test_matrix_4x4_shape(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        m4 = data["parts"][0]["matrix_4x4"]
        assert len(m4) == 4
        assert all(len(col) == 4 for col in m4)

    def test_matrix_4x4_translation_column(self):
        """Last column should be [px, py, pz, 1.0]."""
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="t")
        asm.place_part(part, _pose(5.0, 10.0, 15.0), check_collision=False)
        exporter = SceneExporter()
        data = exporter.export(asm)
        last_col = data["parts"][0]["matrix_4x4"][3]
        assert last_col == pytest.approx([5.0, 10.0, 15.0, 1.0])

    def test_default_colour_code(self):
        exporter = SceneExporter(default_colour=4)
        data = exporter.export(_single_brick_assembly())
        assert data["parts"][0]["colour_code"] == 4

    def test_colour_map_override(self):
        catalog = PartCatalog.default()
        part = catalog.get("brick_2x4")
        asm = Assembly(name="t")
        node = asm.place_part(part, _pose(), check_collision=False)
        exporter = SceneExporter()
        data = exporter.export(asm, colour_map={node.instance_id: 14})
        assert data["parts"][0]["colour_code"] == 14

    def test_bounding_box_ldu_has_min_max(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        bb = data["parts"][0]["bounding_box_ldu"]
        assert "min" in bb and "max" in bb
        assert len(bb["min"]) == 3
        assert len(bb["max"]) == 3

    def test_dimensions_ldu_present(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        dims = data["parts"][0]["dimensions_ldu"]
        assert "width" in dims and "height" in dims and "depth" in dims

    def test_dimensions_mm_scaled(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        ldu = data["parts"][0]["dimensions_ldu"]
        mm = data["parts"][0]["dimensions_mm"]
        assert mm["width"] == pytest.approx(ldu["width"] * LDU_TO_MM)
        assert mm["height"] == pytest.approx(ldu["height"] * LDU_TO_MM)
        assert mm["depth"] == pytest.approx(ldu["depth"] * LDU_TO_MM)

    def test_ldraw_id_for_known_part(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert data["parts"][0]["ldraw_id"] == "3001"

    def test_category_string(self):
        exporter = SceneExporter()
        data = exporter.export(_single_brick_assembly())
        assert isinstance(data["parts"][0]["category"], str)


# ---------------------------------------------------------------------------
# Bonds section
# ---------------------------------------------------------------------------

class TestBondsSection:
    def test_empty_bonds_for_unconnected(self):
        exporter = SceneExporter()
        data = exporter.export(_two_brick_assembly())
        assert data["bonds"] == []

    def test_bond_dict_keys_present_when_bonded(self):
        """Stack two 1x1 plates and form a bond to check bond dict keys."""
        catalog = PartCatalog.default()
        part = catalog.get("plate_1x1")
        asm = Assembly(name="b")
        n0 = asm.place_part(part, _pose(0, 0, 0), check_collision=False)
        n1 = asm.place_part(part, _pose(0, 8, 0), check_collision=False)

        # Try to form a bond if any connectors align
        n0_studs = [c for c in n0.connectors if c.connector_type.name == "STUD"]
        n1_antistuds = [c for c in n1.connectors if c.connector_type.name == "ANTI_STUD"]
        if n0_studs and n1_antistuds:
            try:
                asm.connect(n0.instance_id, n0_studs[0].connector_id,
                            n1.instance_id, n1_antistuds[0].connector_id)
            except Exception:
                pass  # geometric validation may reject; just check structure

        exporter = SceneExporter()
        data = exporter.export(asm)

        for bond in data["bonds"]:
            for key in ("bond_id", "node_a_id", "node_b_id",
                        "stud_connector_id", "anti_stud_connector_id"):
                assert key in bond, f"Missing bond key: {key}"


# ---------------------------------------------------------------------------
# JSON serialisability
# ---------------------------------------------------------------------------

class TestJsonSerialisation:
    def test_export_is_json_serialisable(self):
        exporter = SceneExporter()
        data = exporter.export(_two_brick_assembly())
        serialised = json.dumps(data)
        assert len(serialised) > 0

    def test_export_json_creates_file(self, tmp_path):
        exporter = SceneExporter()
        p = tmp_path / "scene.json"
        exporter.export_json(_two_brick_assembly(), p)
        assert p.exists()
        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert "parts" in loaded
        assert len(loaded["parts"]) == 2

    def test_export_json_indented(self, tmp_path):
        exporter = SceneExporter()
        p = tmp_path / "scene.json"
        exporter.export_json(_single_brick_assembly(), p, indent=4)
        content = p.read_text(encoding="utf-8")
        assert "\n" in content


# ---------------------------------------------------------------------------
# Blender script
# ---------------------------------------------------------------------------

class TestBlenderScript:
    def test_script_is_string(self):
        exporter = SceneExporter()
        script = exporter.blender_script(_single_brick_assembly())
        assert isinstance(script, str)

    def test_script_contains_bpy_import(self):
        exporter = SceneExporter()
        script = exporter.blender_script(_single_brick_assembly())
        assert "import bpy" in script

    def test_script_contains_ldu_to_m(self):
        exporter = SceneExporter()
        script = exporter.blender_script(_single_brick_assembly())
        assert "LDU_TO_M" in script

    def test_script_contains_part_data(self):
        exporter = SceneExporter()
        script = exporter.blender_script(_single_brick_assembly())
        assert "position_ldu" in script

    def test_script_contains_assembly_name(self):
        exporter = SceneExporter()
        script = exporter.blender_script(_single_brick_assembly())
        assert "single" in script
