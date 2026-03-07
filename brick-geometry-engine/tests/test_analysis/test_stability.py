"""Tests for Phase C stability analysis."""

import pytest
from brick_geometry.analysis.stability import StabilityAnalyzer, StabilityReport, NodeStatus
from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.core.transforms import Pose
from brick_geometry.core.constants import BRICK_HEIGHT_LDU
from brick_geometry.parts.common_parts import BRICK_2x4, BRICK_1x2, PLATE_2x4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _analyzer() -> StabilityAnalyzer:
    return StabilityAnalyzer()


def _place(asm: Assembly, part, x=0, y=0, z=0, check_collision=False):
    return asm.place_part(part, Pose.from_xyz(x, y, z), check_collision=check_collision)


# ---------------------------------------------------------------------------
# Empty assembly
# ---------------------------------------------------------------------------

class TestEmptyAssembly:
    def test_empty_is_stable(self):
        asm = Assembly("empty")
        report = _analyzer().analyse(asm)
        assert report.is_stable

    def test_empty_has_no_nodes(self):
        asm = Assembly("empty")
        report = _analyzer().analyse(asm)
        assert report.grounded_nodes == []
        assert report.floating_nodes == []
        assert report.supported_nodes == []
        assert report.isolated_nodes == []

    def test_empty_status_map_empty(self):
        asm = Assembly("empty")
        report = _analyzer().analyse(asm)
        assert report.status_map == {}

    def test_empty_no_errors(self):
        asm = Assembly("empty")
        report = _analyzer().analyse(asm)
        assert report.errors == []


# ---------------------------------------------------------------------------
# Single grounded brick
# ---------------------------------------------------------------------------

class TestGroundedBrick:
    def test_single_brick_at_origin_is_grounded(self):
        asm = Assembly("g")
        node = _place(asm, BRICK_2x4, y=0)
        report = _analyzer().analyse(asm)
        assert report.node_status(node.instance_id) == NodeStatus.GROUNDED

    def test_single_grounded_brick_is_stable(self):
        asm = Assembly("g")
        _place(asm, BRICK_2x4, y=0)
        report = _analyzer().analyse(asm)
        assert report.is_stable

    def test_grounded_brick_in_grounded_list(self):
        asm = Assembly("g")
        node = _place(asm, BRICK_2x4, y=0)
        report = _analyzer().analyse(asm)
        ids = [n.instance_id for n in report.grounded_nodes]
        assert node.instance_id in ids

    def test_grounded_brick_also_in_supported_list(self):
        asm = Assembly("g")
        node = _place(asm, BRICK_2x4, y=0)
        report = _analyzer().analyse(asm)
        ids = [n.instance_id for n in report.supported_nodes]
        assert node.instance_id in ids

    def test_isolated_grounded_generates_warning(self):
        """A grounded brick with no bonds is safe but produces a warning."""
        asm = Assembly("g")
        _place(asm, BRICK_2x4, y=0)
        report = _analyzer().analyse(asm)
        assert len(report.warnings) > 0

    def test_isolated_grounded_in_isolated_list(self):
        asm = Assembly("g")
        node = _place(asm, BRICK_2x4, y=0)
        report = _analyzer().analyse(asm)
        ids = [n.instance_id for n in report.isolated_nodes]
        assert node.instance_id in ids


# ---------------------------------------------------------------------------
# Single floating brick
# ---------------------------------------------------------------------------

class TestFloatingBrick:
    def test_brick_high_in_air_is_floating(self):
        asm = Assembly("f")
        node = _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        assert report.node_status(node.instance_id) in (NodeStatus.FLOATING, NodeStatus.ISOLATED)

    def test_floating_brick_makes_assembly_unstable(self):
        asm = Assembly("f")
        _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        assert not report.is_stable

    def test_floating_brick_produces_error(self):
        asm = Assembly("f")
        _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        assert len(report.errors) > 0

    def test_floating_brick_in_floating_list(self):
        asm = Assembly("f")
        node = _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        ids = [n.instance_id for n in report.floating_nodes]
        assert node.instance_id in ids

    def test_floating_count(self):
        asm = Assembly("f")
        _place(asm, BRICK_2x4, y=500)
        _place(asm, BRICK_2x4, y=600)
        report = _analyzer().analyse(asm)
        assert report.floating_count() == 2


# ---------------------------------------------------------------------------
# Mixed assembly: one grounded, one floating
# ---------------------------------------------------------------------------

class TestMixedAssembly:
    def test_grounded_ok_floating_not(self):
        asm = Assembly("m")
        grounded = _place(asm, BRICK_2x4, y=0)
        floating = _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        assert report.node_status(grounded.instance_id) == NodeStatus.GROUNDED
        assert report.node_status(floating.instance_id) in (NodeStatus.FLOATING, NodeStatus.ISOLATED)
        assert not report.is_stable

    def test_grounded_count(self):
        asm = Assembly("m")
        _place(asm, BRICK_2x4, y=0)
        _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        assert report.grounded_count() == 1

    def test_two_grounded_bricks(self):
        asm = Assembly("m")
        _place(asm, BRICK_2x4, x=0, y=0, z=0)
        _place(asm, BRICK_2x4, x=100, y=0, z=0)
        report = _analyzer().analyse(asm)
        assert report.grounded_count() == 2
        assert report.is_stable


# ---------------------------------------------------------------------------
# Supported bricks (bonded to grounded)
# ---------------------------------------------------------------------------

class TestSupportedBricks:
    def _stacked_assembly(self):
        """Bottom brick grounded at y=0; top brick stacked at y=BRICK_HEIGHT."""
        asm = Assembly("s")
        bottom = asm.place_part(BRICK_2x4, Pose.identity())
        top = asm.place_part(BRICK_2x4, Pose.from_xyz(0, BRICK_HEIGHT_LDU, 0))
        asm.connect(
            bottom.instance_id, "stud_0_0",
            top.instance_id, "anti_stud_0_0",
        )
        return asm, bottom, top

    def test_bottom_is_grounded(self):
        asm, bottom, top = self._stacked_assembly()
        report = _analyzer().analyse(asm)
        assert report.node_status(bottom.instance_id) == NodeStatus.GROUNDED

    def test_top_is_supported(self):
        asm, bottom, top = self._stacked_assembly()
        report = _analyzer().analyse(asm)
        assert report.node_status(top.instance_id) == NodeStatus.SUPPORTED

    def test_stacked_assembly_is_stable(self):
        asm, bottom, top = self._stacked_assembly()
        report = _analyzer().analyse(asm)
        assert report.is_stable

    def test_top_in_supported_list(self):
        asm, bottom, top = self._stacked_assembly()
        report = _analyzer().analyse(asm)
        sup_ids = {n.instance_id for n in report.supported_nodes}
        assert top.instance_id in sup_ids

    def test_supported_not_in_floating(self):
        asm, bottom, top = self._stacked_assembly()
        report = _analyzer().analyse(asm)
        float_ids = {n.instance_id for n in report.floating_nodes}
        assert top.instance_id not in float_ids

    def test_no_errors_when_fully_supported(self):
        asm, bottom, top = self._stacked_assembly()
        report = _analyzer().analyse(asm)
        assert report.errors == []


# ---------------------------------------------------------------------------
# NodeStatus queries
# ---------------------------------------------------------------------------

class TestNodeStatus:
    def test_node_status_raises_for_unknown_id(self):
        asm = Assembly("q")
        report = _analyzer().analyse(asm)
        with pytest.raises(KeyError):
            report.node_status("nonexistent-id")

    def test_status_map_has_all_nodes(self):
        asm = Assembly("q")
        n0 = _place(asm, BRICK_2x4, y=0)
        n1 = _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        assert n0.instance_id in report.status_map
        assert n1.instance_id in report.status_map


# ---------------------------------------------------------------------------
# Custom ground plane
# ---------------------------------------------------------------------------

class TestCustomGroundPlane:
    def test_custom_ground_y(self):
        """Place brick at y=100; with ground_y=100 it should be grounded."""
        analyzer = StabilityAnalyzer(ground_y=100.0)
        asm = Assembly("cg")
        node = _place(asm, BRICK_2x4, y=100)
        report = analyzer.analyse(asm)
        assert report.node_status(node.instance_id) == NodeStatus.GROUNDED

    def test_default_ground_y_in_report(self):
        report = _analyzer().analyse(Assembly("r"))
        assert report.ground_y == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# StabilityReport repr and helpers
# ---------------------------------------------------------------------------

class TestReportHelpers:
    def test_repr_stable(self):
        asm = Assembly("r")
        _place(asm, BRICK_2x4, y=0)
        report = _analyzer().analyse(asm)
        assert "STABLE" in repr(report)

    def test_repr_unstable(self):
        asm = Assembly("r")
        _place(asm, BRICK_2x4, y=500)
        report = _analyzer().analyse(asm)
        r = repr(report)
        assert "floating" in r or "1" in r

    def test_is_node_grounded_true(self):
        analyzer = _analyzer()
        asm = Assembly("r")
        node = _place(asm, BRICK_2x4, y=0)
        assert analyzer.is_node_grounded(node) is True

    def test_is_node_grounded_false(self):
        analyzer = _analyzer()
        asm = Assembly("r")
        node = _place(asm, BRICK_2x4, y=500)
        assert analyzer.is_node_grounded(node) is False


# ---------------------------------------------------------------------------
# Floating component summary warning
# ---------------------------------------------------------------------------

class TestFloatingComponentWarning:
    def test_two_bonded_floating_bricks_generate_warning(self):
        """Two bricks bonded to each other but not to ground → component warning."""
        asm = Assembly("fc")
        b0 = asm.place_part(BRICK_2x4, Pose.from_xyz(0, 500, 0))
        b1 = asm.place_part(BRICK_2x4, Pose.from_xyz(0, 500 + BRICK_HEIGHT_LDU, 0))
        asm.connect(
            b0.instance_id, "stud_0_0",
            b1.instance_id, "anti_stud_0_0",
        )
        report = _analyzer().analyse(asm)
        # Both should be floating
        assert report.floating_count() == 2
        # Should generate a component-level warning
        component_warnings = [w for w in report.warnings if "component" in w.lower()]
        assert len(component_warnings) >= 1
