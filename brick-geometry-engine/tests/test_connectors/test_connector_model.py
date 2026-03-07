import pytest
from brick_geometry.core.geometry import Point3D, Vector3D
from brick_geometry.connectors.connector_model import (
    Connector, ConnectorPair, ConnectorType, ConnectorState
)
from brick_geometry.core.constants import STUD_DIAMETER_LDU, STUD_HEIGHT_LDU, ANTI_STUD_DIAMETER_LDU


def make_stud(cid="stud_0_0"):
    return Connector(
        connector_id=cid,
        connector_type=ConnectorType.STUD,
        position=Point3D(10, 24, 10),
        normal=Vector3D(0, 1, 0),
    )

def make_anti_stud(cid="anti_stud_0_0"):
    return Connector(
        connector_id=cid,
        connector_type=ConnectorType.ANTI_STUD,
        position=Point3D(10, 24, 10),
        normal=Vector3D(0, -1, 0),
    )


class TestConnector:
    def test_initial_state_free(self):
        s = make_stud()
        assert s.is_free
        assert s.state == ConnectorState.FREE

    def test_stud_diameter(self):
        assert make_stud().diameter == STUD_DIAMETER_LDU

    def test_anti_stud_diameter(self):
        assert make_anti_stud().diameter == ANTI_STUD_DIAMETER_LDU

    def test_stud_height(self):
        assert make_stud().height == STUD_HEIGHT_LDU

    def test_anti_stud_height_zero(self):
        assert make_anti_stud().height == 0.0

    def test_mating_point_stud(self):
        s = make_stud()
        mp = s.mating_point()
        assert mp.y == pytest.approx(24 + STUD_HEIGHT_LDU)

    def test_mating_point_anti_stud(self):
        a = make_anti_stud()
        mp = a.mating_point()
        assert mp == a.position

    def test_occupy_and_release(self):
        s = make_stud()
        a = make_anti_stud()
        s.occupy(a)
        assert not s.is_free
        assert s.connected_to is a
        s.release()
        assert s.is_free
        assert s.connected_to is None

    def test_equality(self):
        s1 = make_stud("s1")
        s2 = make_stud("s1")
        assert s1 == s2

    def test_hash(self):
        s = make_stud()
        {s}  # must be hashable


class TestConnectorPair:
    def test_valid_pair(self):
        s = make_stud()
        a = make_anti_stud()
        pair = ConnectorPair(stud=s, anti_stud=a)
        assert pair.stud is s
        assert pair.anti_stud is a

    def test_wrong_order_raises(self):
        s = make_stud()
        a = make_anti_stud()
        with pytest.raises(ValueError):
            ConnectorPair(stud=a, anti_stud=s)

    def test_same_type_raises(self):
        s1 = make_stud("s1")
        s2 = make_stud("s2")
        with pytest.raises(ValueError):
            ConnectorPair(stud=s1, anti_stud=s2)
