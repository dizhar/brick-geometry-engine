import pytest
from brick_geometry.core.coordinates import (
    ldu_to_mm, mm_to_ldu,
    studs_to_ldu, ldu_to_studs,
    plates_to_ldu, ldu_to_plates,
    bricks_to_ldu, ldu_to_bricks,
    snap_to_stud_grid, snap_to_plate_grid, snap_position,
    is_on_stud_grid, is_on_plate_grid, is_valid_grid_position,
    GridPosition,
)
from brick_geometry.core.constants import (
    STUD_SPACING_LDU, PLATE_HEIGHT_LDU, BRICK_HEIGHT_LDU, LDU_TO_MM
)


class TestUnitConversions:
    def test_ldu_to_mm(self):
        assert ldu_to_mm(20) == pytest.approx(8.0)
        assert ldu_to_mm(0) == 0.0

    def test_mm_to_ldu(self):
        assert mm_to_ldu(8.0) == pytest.approx(20.0)

    def test_round_trip_ldu_mm(self):
        for v in [0, 10, 20, 100]:
            assert mm_to_ldu(ldu_to_mm(v)) == pytest.approx(v)

    def test_studs_to_ldu(self):
        assert studs_to_ldu(1) == STUD_SPACING_LDU
        assert studs_to_ldu(4) == 4 * STUD_SPACING_LDU

    def test_ldu_to_studs(self):
        assert ldu_to_studs(STUD_SPACING_LDU) == pytest.approx(1.0)

    def test_plates_to_ldu(self):
        assert plates_to_ldu(1) == PLATE_HEIGHT_LDU
        assert plates_to_ldu(3) == BRICK_HEIGHT_LDU

    def test_ldu_to_plates(self):
        assert ldu_to_plates(PLATE_HEIGHT_LDU) == pytest.approx(1.0)
        assert ldu_to_plates(BRICK_HEIGHT_LDU) == pytest.approx(3.0)

    def test_bricks_to_ldu(self):
        assert bricks_to_ldu(1) == BRICK_HEIGHT_LDU
        assert bricks_to_ldu(2) == 2 * BRICK_HEIGHT_LDU

    def test_ldu_to_bricks(self):
        assert ldu_to_bricks(BRICK_HEIGHT_LDU) == pytest.approx(1.0)


class TestGridSnapping:
    def test_snap_to_stud_grid_already_on(self):
        assert snap_to_stud_grid(0) == 0
        assert snap_to_stud_grid(20) == 20
        assert snap_to_stud_grid(40) == 40

    def test_snap_to_stud_grid_rounds(self):
        assert snap_to_stud_grid(9) == 0
        assert snap_to_stud_grid(11) == 20
        assert snap_to_stud_grid(29) == 20
        assert snap_to_stud_grid(31) == 40

    def test_snap_to_plate_grid_already_on(self):
        assert snap_to_plate_grid(0) == 0
        assert snap_to_plate_grid(8) == 8
        assert snap_to_plate_grid(24) == 24

    def test_snap_to_plate_grid_rounds(self):
        assert snap_to_plate_grid(3) == 0
        assert snap_to_plate_grid(5) == 8

    def test_snap_position(self):
        x, y, z = snap_position(11, 5, 29)
        assert x == 20
        assert y == 8
        assert z == 20


class TestGridValidation:
    def test_is_on_stud_grid_true(self):
        assert is_on_stud_grid(0)
        assert is_on_stud_grid(20)
        assert is_on_stud_grid(100)

    def test_is_on_stud_grid_false(self):
        assert not is_on_stud_grid(1)
        assert not is_on_stud_grid(15)

    def test_is_on_plate_grid_true(self):
        assert is_on_plate_grid(0)
        assert is_on_plate_grid(8)
        assert is_on_plate_grid(24)

    def test_is_on_plate_grid_false(self):
        assert not is_on_plate_grid(1)
        assert not is_on_plate_grid(10)

    def test_is_valid_grid_position(self):
        assert is_valid_grid_position(0, 0, 0)
        assert is_valid_grid_position(20, 8, 40)
        assert not is_valid_grid_position(1, 0, 0)
        assert not is_valid_grid_position(0, 1, 0)


class TestGridPosition:
    def test_to_ldu(self):
        gp = GridPosition(col=1, layer=0, row=2)
        x, y, z = gp.to_ldu()
        assert x == STUD_SPACING_LDU
        assert y == 0
        assert z == 2 * STUD_SPACING_LDU

    def test_from_ldu(self):
        gp = GridPosition.from_ldu(20, 8, 40)
        assert gp.col == 1
        assert gp.layer == 1
        assert gp.row == 2

    def test_round_trip(self):
        gp = GridPosition(col=3, layer=2, row=5)
        x, y, z = gp.to_ldu()
        gp2 = GridPosition.from_ldu(x, y, z)
        assert gp == gp2
