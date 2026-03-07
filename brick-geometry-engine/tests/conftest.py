"""Shared pytest fixtures."""
import pytest
from brick_geometry.core.geometry import Point3D, Vector3D, BoundingBox
from brick_geometry.core.transforms import Pose, Rotation
from brick_geometry.parts.common_parts import BRICK_2x4, BRICK_1x2, PLATE_2x4, PLATE_1x1
from brick_geometry.assembly.assembly_graph import Assembly


@pytest.fixture
def brick_2x4():
    return BRICK_2x4

@pytest.fixture
def brick_1x2():
    return BRICK_1x2

@pytest.fixture
def plate_2x4():
    return PLATE_2x4

@pytest.fixture
def plate_1x1():
    return PLATE_1x1

@pytest.fixture
def origin_pose():
    return Pose.identity()

@pytest.fixture
def empty_assembly():
    return Assembly("test_assembly")
