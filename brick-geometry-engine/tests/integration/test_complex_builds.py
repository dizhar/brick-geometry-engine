"""
Integration tests: more complex assembly scenarios.
"""
import pytest
from brick_geometry.core.transforms import Pose, Rotation
from brick_geometry.core.constants import BRICK_HEIGHT_LDU, STUD_SPACING_LDU
from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.assembly.placement_engine import PlacementEngine
from brick_geometry.parts.common_parts import (
    BRICK_2x4, BRICK_1x2, BRICK_2x2, PLATE_2x4, PLATE_1x1
)


class TestWallConstruction:
    """Build a simple 2-brick-wide, 2-course wall (4 bricks total)."""

    def _build_wall(self):
        asm = Assembly("wall")
        # Course 1: two 2x4 bricks side-by-side along Z (no gap needed; touching ok)
        b00 = asm.place_part(BRICK_2x4, Pose.from_xyz(0, 0, 0))
        # second brick starts at z = 4 studs = 80 LDU (touching boundary, not overlapping)
        b01 = asm.place_part(BRICK_2x4, Pose.from_xyz(0, 0, 4 * STUD_SPACING_LDU))
        # Course 2: offset by 2 studs (running bond), one brick higher
        b10 = asm.place_part(
            BRICK_2x4,
            Pose.from_xyz(0, BRICK_HEIGHT_LDU, 2 * STUD_SPACING_LDU),
        )
        return asm, [b00, b01, b10]

    def test_wall_places_three_bricks(self):
        asm, nodes = self._build_wall()
        assert len(asm) == 3

    def test_wall_no_collision_first_course(self):
        asm = Assembly("wall")
        asm.place_part(BRICK_2x4, Pose.from_xyz(0, 0, 0))
        asm.place_part(BRICK_2x4, Pose.from_xyz(0, 0, 4 * STUD_SPACING_LDU))

    def test_wall_connect_courses(self):
        asm, nodes = self._build_wall()
        # stud_0_2 is at z-index 2 on bottom brick, anti_stud_0_0 on top brick
        # bottom stud_0_2 is at z=50; top brick placed at z_offset=40,
        # so anti_stud_0_0 on top brick is at world z=40+10=50 — they align
        asm.connect(nodes[0].instance_id, "stud_0_2",
                    nodes[2].instance_id, "anti_stud_0_0")
        assert asm.bond_count() >= 1


class TestRotatedPlacement:
    """Place parts at 90° rotations."""

    def test_rotated_brick_no_collision(self):
        asm = Assembly("rotated")
        r90 = Rotation.from_axis_angle_90("y", 1)
        asm.place_part(BRICK_2x4, Pose(Pose.identity().position, r90))
        assert len(asm) == 1

    def test_four_bricks_pinwheel(self):
        """Four 1x2 bricks in a pinwheel pattern, one per rotation."""
        asm = Assembly("pinwheel")
        offsets = [(0, 0), (2 * STUD_SPACING_LDU, 0),
                   (0, 2 * STUD_SPACING_LDU), (2 * STUD_SPACING_LDU, 2 * STUD_SPACING_LDU)]
        rotations = [Rotation.from_axis_angle_90("y", s) for s in range(4)]
        for (ox, oz), rot in zip(offsets, rotations):
            from brick_geometry.core.geometry import Point3D
            asm.place_part(
                BRICK_1x2,
                Pose(Point3D(ox, 0, oz), rot),
                check_collision=False,
            )
        assert len(asm) == 4


class TestAssemblyGraphIntegrity:
    def test_path_through_assembly(self):
        asm = Assembly("path")
        nodes = []
        for i in range(5):
            n = asm.place_part(BRICK_2x4, Pose.from_xyz(0, i * BRICK_HEIGHT_LDU, 0))
            nodes.append(n)
        for i in range(4):
            asm.connect(
                nodes[i].instance_id, "stud_0_0",
                nodes[i + 1].instance_id, "anti_stud_0_0",
            )
        path = asm.find_path(nodes[0].instance_id, nodes[4].instance_id)
        assert path is not None
        assert len(path) == 5

    def test_validate_after_complex_build(self):
        asm = Assembly("complex")
        base = asm.place_part(BRICK_2x4, Pose.identity())
        top = asm.place_part(BRICK_2x4, Pose.from_xyz(0, BRICK_HEIGHT_LDU, 0))
        # BRICK_2x2 placed to the side — starts at x=2*20=40, base ends at x=40: touching ok
        side = asm.place_part(BRICK_2x2, Pose.from_xyz(2 * STUD_SPACING_LDU, 0, 0))
        asm.connect(base.instance_id, "stud_0_0", top.instance_id, "anti_stud_0_0")
        report = asm.validate()
        # Two connected components (base+top and side), so warnings but no errors
        assert report.is_valid

    def test_serialise_to_dict(self):
        asm = Assembly("serial")
        n = asm.place_part(BRICK_2x4, Pose.identity())
        d = asm.to_dict()
        assert d["name"] == "serial"
        assert len(d["nodes"]) == 1
        assert len(d["bonds"]) == 0


class TestPlacementEngine:
    def test_suggest_placements_on_first_brick(self):
        asm = Assembly("engine_test")
        base = asm.place_part(BRICK_2x4, Pose.identity())
        engine = PlacementEngine(asm)
        suggestions = engine.suggest_placements(BRICK_1x2, anchor_node_id=base.instance_id)
        assert len(suggestions) > 0

    def test_is_placement_valid_clear_spot(self):
        asm = Assembly("valid_check")
        asm.place_part(BRICK_2x4, Pose.identity())
        engine = PlacementEngine(asm)
        assert engine.is_placement_valid(BRICK_2x4, Pose.from_xyz(1000, 0, 0))

    def test_is_placement_valid_overlap(self):
        asm = Assembly("invalid_check")
        asm.place_part(BRICK_2x4, Pose.identity())
        engine = PlacementEngine(asm)
        assert not engine.is_placement_valid(BRICK_2x4, Pose.identity())
