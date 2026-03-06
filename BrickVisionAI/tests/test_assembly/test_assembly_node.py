import pytest
from brick_geometry.core.transforms import Pose
from brick_geometry.core.constants import STUD_SPACING_LDU, BRICK_HEIGHT_LDU
from brick_geometry.connectors.connector_model import ConnectorType
from brick_geometry.assembly.assembly_node import AssemblyNode, generate_connectors
from brick_geometry.parts.common_parts import BRICK_2x4, BRICK_1x2, PLATE_1x1


class TestGenerateConnectors:
    def test_count(self):
        # 2x4 brick: 2*4 studs + 2*4 anti-studs = 16
        conns = generate_connectors(BRICK_2x4, Pose.identity())
        assert len(conns) == 2 * 4 * 2

    def test_stud_count(self):
        conns = generate_connectors(BRICK_2x4, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        assert len(studs) == 8

    def test_anti_stud_count(self):
        conns = generate_connectors(BRICK_2x4, Pose.identity())
        anti = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        assert len(anti) == 8

    def test_stud_y_position(self):
        conns = generate_connectors(BRICK_2x4, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        for s in studs:
            assert s.position.y == pytest.approx(BRICK_HEIGHT_LDU)

    def test_anti_stud_y_position(self):
        conns = generate_connectors(BRICK_2x4, Pose.identity())
        anti = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        for a in anti:
            assert a.position.y == pytest.approx(0.0)

    def test_stud_normal_up(self):
        conns = generate_connectors(BRICK_2x4, Pose.identity())
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        for s in studs:
            assert s.normal.y == pytest.approx(1.0)

    def test_anti_stud_normal_down(self):
        conns = generate_connectors(BRICK_2x4, Pose.identity())
        anti = [c for c in conns if c.connector_type == ConnectorType.ANTI_STUD]
        for a in anti:
            assert a.normal.y == pytest.approx(-1.0)

    def test_1x1_plate_count(self):
        conns = generate_connectors(PLATE_1x1, Pose.identity())
        assert len(conns) == 2  # 1 stud + 1 anti-stud

    def test_translated_pose_shifts_connectors(self):
        offset = 100.0
        conns = generate_connectors(BRICK_2x4, Pose.from_xyz(offset, 0, 0))
        studs = [c for c in conns if c.connector_type == ConnectorType.STUD]
        for s in studs:
            assert s.position.x >= offset


class TestAssemblyNode:
    def test_create(self):
        node = AssemblyNode(BRICK_2x4, Pose.identity())
        assert node.part is BRICK_2x4
        assert node.instance_id

    def test_custom_instance_id(self):
        node = AssemblyNode(BRICK_2x4, Pose.identity(), instance_id="my_id")
        assert node.instance_id == "my_id"

    def test_connectors_generated(self):
        node = AssemblyNode(BRICK_2x4, Pose.identity())
        assert len(node.connectors) == 16

    def test_get_connector(self):
        node = AssemblyNode(BRICK_2x4, Pose.identity())
        c = node.get_connector("stud_0_0")
        assert c.connector_id == "stud_0_0"

    def test_get_connector_missing_raises(self):
        node = AssemblyNode(BRICK_2x4, Pose.identity())
        with pytest.raises(KeyError):
            node.get_connector("nonexistent")

    def test_free_connectors_all_initially(self):
        node = AssemblyNode(BRICK_2x4, Pose.identity())
        assert len(node.free_connectors()) == len(node.connectors)

    def test_pose_setter_no_connections(self):
        node = AssemblyNode(BRICK_2x4, Pose.identity())
        node.pose = Pose.from_xyz(100, 0, 0)
        assert node.pose.position.x == pytest.approx(100)

    def test_clone(self):
        node = AssemblyNode(BRICK_2x4, Pose.from_xyz(10, 0, 0), instance_id="orig")
        clone = node.clone()
        assert clone.instance_id != "orig"
        assert clone.part is node.part
        assert clone.pose == node.pose
