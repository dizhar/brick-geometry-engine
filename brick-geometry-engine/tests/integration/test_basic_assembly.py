"""
Integration tests: basic assembly workflows.

These tests exercise the full stack — parts → connectors → assembly graph.
"""
import pytest
from brick_geometry.core.transforms import Pose
from brick_geometry.core.constants import BRICK_HEIGHT_LDU, PLATE_HEIGHT_LDU, STUD_SPACING_LDU
from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.assembly.placement_engine import PlacementEngine
from brick_geometry.parts.common_parts import BRICK_2x4, BRICK_1x2, PLATE_2x4, PLATE_1x1


class TestSimpleTower:
    """Stack three 2x4 bricks into a vertical tower."""

    def setup_method(self):
        self.asm = Assembly("tower")

    def test_place_three_bricks(self):
        for i in range(3):
            self.asm.place_part(
                BRICK_2x4,
                Pose.from_xyz(0, i * BRICK_HEIGHT_LDU, 0),
                check_collision=False,
            )
        assert len(self.asm) == 3

    def test_connect_stack(self):
        nodes = [
            self.asm.place_part(BRICK_2x4, Pose.from_xyz(0, i * BRICK_HEIGHT_LDU, 0))
            for i in range(3)
        ]
        for i in range(2):
            self.asm.connect(
                nodes[i].instance_id, "stud_0_0",
                nodes[i + 1].instance_id, "anti_stud_0_0",
            )
        assert self.asm.bond_count() == 2
        assert self.asm.is_fully_connected()

    def test_stack_validates(self):
        nodes = [
            self.asm.place_part(BRICK_2x4, Pose.from_xyz(0, i * BRICK_HEIGHT_LDU, 0))
            for i in range(3)
        ]
        for i in range(2):
            self.asm.connect(
                nodes[i].instance_id, "stud_0_0",
                nodes[i + 1].instance_id, "anti_stud_0_0",
            )
        report = self.asm.validate()
        assert report.is_valid


class TestMixedPartTypes:
    """Combine bricks and plates."""

    def test_brick_on_plate(self):
        asm = Assembly("mixed")
        plate = asm.place_part(PLATE_2x4, Pose.identity())
        brick = asm.place_part(BRICK_2x4, Pose.from_xyz(0, PLATE_HEIGHT_LDU, 0))
        pair = asm.connect(
            plate.instance_id, "stud_0_0",
            brick.instance_id, "anti_stud_0_0",
        )
        assert pair is not None
        assert asm.is_fully_connected()

    def test_three_plates_equal_one_brick(self):
        """3 stacked plates have same height as 1 brick."""
        assert 3 * PLATE_HEIGHT_LDU == BRICK_HEIGHT_LDU


class TestDisassembly:
    def test_remove_middle_splits_components(self):
        asm = Assembly("disassembly")
        n0 = asm.place_part(BRICK_2x4, Pose.from_xyz(0, 0, 0))
        n1 = asm.place_part(BRICK_2x4, Pose.from_xyz(0, BRICK_HEIGHT_LDU, 0))
        n2 = asm.place_part(BRICK_2x4, Pose.from_xyz(0, 2 * BRICK_HEIGHT_LDU, 0))
        asm.connect(n0.instance_id, "stud_0_0", n1.instance_id, "anti_stud_0_0")
        asm.connect(n1.instance_id, "stud_0_0", n2.instance_id, "anti_stud_0_0")
        assert asm.is_fully_connected()
        asm.remove_part(n1.instance_id)
        assert len(asm.connected_components()) == 2

    def test_disconnect_frees_connectors(self):
        asm = Assembly("free")
        bottom = asm.place_part(BRICK_2x4, Pose.identity())
        top = asm.place_part(BRICK_2x4, Pose.from_xyz(0, BRICK_HEIGHT_LDU, 0))
        asm.connect(bottom.instance_id, "stud_0_0", top.instance_id, "anti_stud_0_0")
        bond_id = list(asm._bonds.keys())[0]
        asm.disconnect(bond_id)
        stud = bottom.get_connector("stud_0_0")
        anti = top.get_connector("anti_stud_0_0")
        assert stud.is_free
        assert anti.is_free


class TestCatalogIntegration:
    def test_default_catalog_parts_work_in_assembly(self):
        from brick_geometry.parts.part_catalog import PartCatalog
        catalog = PartCatalog.default()
        asm = Assembly("catalog_test")
        part = catalog.get("brick_2x4")
        node = asm.place_part(part, Pose.identity())
        assert node.part.part_id == "brick_2x4"
        assert len(node.connectors) == 16
