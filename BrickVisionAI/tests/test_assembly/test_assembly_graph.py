import pytest
from brick_geometry.core.transforms import Pose
from brick_geometry.core.constants import BRICK_HEIGHT_LDU
from brick_geometry.assembly.assembly_graph import Assembly
from brick_geometry.parts.common_parts import BRICK_2x4, BRICK_1x2, PLATE_2x4


def make_assembly():
    return Assembly("test")


class TestAssemblyPlacement:
    def test_place_part_returns_node(self):
        asm = make_assembly()
        node = asm.place_part(BRICK_2x4, Pose.identity())
        assert node.part is BRICK_2x4

    def test_place_adds_to_assembly(self):
        asm = make_assembly()
        node = asm.place_part(BRICK_2x4, Pose.identity())
        assert node.instance_id in asm

    def test_duplicate_id_raises(self):
        asm = make_assembly()
        asm.place_part(BRICK_2x4, Pose.identity(), instance_id="x")
        with pytest.raises(ValueError):
            asm.place_part(BRICK_2x4, Pose.identity(), instance_id="x")

    def test_collision_raises(self):
        asm = make_assembly()
        asm.place_part(BRICK_2x4, Pose.identity())
        with pytest.raises(ValueError):
            asm.place_part(BRICK_2x4, Pose.identity())

    def test_no_collision_skip(self):
        asm = make_assembly()
        asm.place_part(BRICK_2x4, Pose.identity())
        # should not raise with check disabled
        asm.place_part(BRICK_2x4, Pose.identity(), check_collision=False)

    def test_remove_part(self):
        asm = make_assembly()
        node = asm.place_part(BRICK_2x4, Pose.identity())
        asm.remove_part(node.instance_id)
        assert node.instance_id not in asm

    def test_len(self):
        asm = make_assembly()
        assert len(asm) == 0
        asm.place_part(BRICK_2x4, Pose.identity())
        assert len(asm) == 1

    def test_get_node(self):
        asm = make_assembly()
        node = asm.place_part(BRICK_2x4, Pose.identity())
        assert asm.get_node(node.instance_id) is node

    def test_get_node_missing_raises(self):
        asm = make_assembly()
        with pytest.raises(KeyError):
            asm.get_node("nonexistent")


class TestAssemblyConnections:
    def _stacked(self):
        """Place two bricks stacked, return (assembly, bottom, top)."""
        asm = make_assembly()
        bottom = asm.place_part(BRICK_2x4, Pose.identity())
        top = asm.place_part(BRICK_2x4, Pose.from_xyz(0, BRICK_HEIGHT_LDU, 0))
        return asm, bottom, top

    def test_connect(self):
        asm, bottom, top = self._stacked()
        pair = asm.connect(
            bottom.instance_id, "stud_0_0",
            top.instance_id, "anti_stud_0_0",
        )
        assert pair is not None
        assert asm.bond_count() == 1

    def test_disconnect(self):
        asm, bottom, top = self._stacked()
        asm.connect(bottom.instance_id, "stud_0_0", top.instance_id, "anti_stud_0_0")
        bond_id = list(asm._bonds.keys())[0]
        asm.disconnect(bond_id)
        assert asm.bond_count() == 0

    def test_disconnect_nodes(self):
        asm, bottom, top = self._stacked()
        asm.connect(bottom.instance_id, "stud_0_0", top.instance_id, "anti_stud_0_0")
        asm.connect(bottom.instance_id, "stud_0_1", top.instance_id, "anti_stud_0_1")
        n = asm.disconnect_nodes(bottom.instance_id, top.instance_id)
        assert n == 2
        assert asm.bond_count() == 0

    def test_remove_part_breaks_bonds(self):
        asm, bottom, top = self._stacked()
        asm.connect(bottom.instance_id, "stud_0_0", top.instance_id, "anti_stud_0_0")
        asm.remove_part(top.instance_id)
        assert asm.bond_count() == 0

    def test_connect_bad_type_raises(self):
        asm, bottom, top = self._stacked()
        with pytest.raises(ValueError):
            # anti_stud→anti_stud is invalid
            asm.connect(bottom.instance_id, "anti_stud_0_0", top.instance_id, "anti_stud_0_0")


class TestAssemblyTraversal:
    def _chain(self, length=3):
        """Stack *length* bricks vertically so connectors align."""
        asm = make_assembly()
        nodes = []
        for i in range(length):
            n = asm.place_part(
                BRICK_2x4,
                Pose.from_xyz(0, i * BRICK_HEIGHT_LDU, 0),
            )
            nodes.append(n)
        # connect consecutive nodes
        for i in range(length - 1):
            asm.connect(
                nodes[i].instance_id, "stud_0_0",
                nodes[i + 1].instance_id, "anti_stud_0_0",
            )
        return asm, nodes

    def test_neighbours(self):
        asm, nodes = self._chain(3)
        nbrs = asm.neighbours(nodes[1].instance_id)
        ids = {n.instance_id for n in nbrs}
        assert nodes[0].instance_id in ids
        assert nodes[2].instance_id in ids

    def test_bfs_visits_all(self):
        asm, nodes = self._chain(3)
        visited = list(asm.bfs(nodes[0].instance_id))
        assert len(visited) == 3

    def test_dfs_visits_all(self):
        asm, nodes = self._chain(3)
        visited = list(asm.dfs(nodes[0].instance_id))
        assert len(visited) == 3

    def test_connected_components_single(self):
        asm, nodes = self._chain(3)
        comps = asm.connected_components()
        assert len(comps) == 1

    def test_connected_components_multiple(self):
        asm = make_assembly()
        asm.place_part(BRICK_2x4, Pose.identity())
        asm.place_part(BRICK_2x4, Pose.from_xyz(1000, 0, 0))
        comps = asm.connected_components()
        assert len(comps) == 2

    def test_is_fully_connected_true(self):
        asm, _ = self._chain(3)
        assert asm.is_fully_connected()

    def test_is_fully_connected_false(self):
        asm = make_assembly()
        asm.place_part(BRICK_2x4, Pose.identity())
        asm.place_part(BRICK_2x4, Pose.from_xyz(1000, 0, 0))
        assert not asm.is_fully_connected()

    def test_find_path_direct(self):
        asm, nodes = self._chain(2)
        path = asm.find_path(nodes[0].instance_id, nodes[1].instance_id)
        assert path is not None
        assert len(path) == 2

    def test_find_path_no_connection(self):
        asm = make_assembly()
        a = asm.place_part(BRICK_2x4, Pose.identity())
        b = asm.place_part(BRICK_2x4, Pose.from_xyz(1000, 0, 0))
        assert asm.find_path(a.instance_id, b.instance_id) is None

    def test_find_path_self(self):
        asm, nodes = self._chain(1)
        path = asm.find_path(nodes[0].instance_id, nodes[0].instance_id)
        assert path is not None
        assert len(path) == 1


class TestAssemblyValidation:
    def test_empty_assembly_valid(self):
        asm = make_assembly()
        report = asm.validate()
        assert report.is_valid

    def test_valid_assembly(self):
        asm = make_assembly()
        bottom = asm.place_part(BRICK_2x4, Pose.identity())
        top = asm.place_part(
            BRICK_2x4, Pose.from_xyz(0, BRICK_HEIGHT_LDU, 0), check_collision=False
        )
        asm.connect(bottom.instance_id, "stud_0_0", top.instance_id, "anti_stud_0_0")
        report = asm.validate()
        assert report.is_valid

    def test_isolated_node_warning(self):
        asm = make_assembly()
        asm.place_part(BRICK_2x4, Pose.identity())
        asm.place_part(BRICK_2x4, Pose.from_xyz(1000, 0, 0))
        report = asm.validate()
        assert len(report.warnings) > 0
