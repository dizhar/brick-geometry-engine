"""
Phase B connector generation for slope and Technic parts.

Standard bricks and plates are handled by generate_connectors() in
assembly_node.py.  This module provides specialised generators for the
two new Phase B part families and a top-level dispatcher that replaces
direct calls to the old helper.
"""

from __future__ import annotations

from typing import List

from ..core.geometry import Point3D, Vector3D
from ..core.transforms import Pose
from ..core.constants import STUD_SPACING_LDU, BRICK_HEIGHT_LDU
from ..parts.part_metadata import PartCategory, PartMetadata
from .connector_model import Connector, ConnectorType


# ---------------------------------------------------------------------------
# Internal helpers shared with the standard generator
# ---------------------------------------------------------------------------

def _stud_normal_local() -> Vector3D:
    return Vector3D(0.0, 1.0, 0.0)


def _anti_stud_normal_local() -> Vector3D:
    return Vector3D(0.0, -1.0, 0.0)


# ---------------------------------------------------------------------------
# Slope connector generation
# ---------------------------------------------------------------------------

def generate_slope_connectors(part: PartMetadata, pose: Pose) -> List[Connector]:
    """
    Generate world-space connectors for a SLOPE part.

    Layout
    ------
    Anti-studs (bottom face):
        All stud-grid positions — slopes sit on flat surfaces just like bricks.

    Studs (top face):
        Only the rows at the *high* (back) end of the slope where a flat
        horizontal surface exists.  The number of flat rows is given by
        ``part.slope_geometry.flat_rows_at_high_end``.  Studs sit at the
        maximum height (``dimensions.height_ldu``).
    """
    dims = part.dimensions
    sg = part.slope_geometry
    flat_rows = sg.flat_rows_at_high_end if sg is not None else 1
    connectors: List[Connector] = []

    stud_n_local = _stud_normal_local()
    anti_n_local = _anti_stud_normal_local()

    for col in range(dims.studs_x):
        for row in range(dims.studs_z):
            local_x = (col + 0.5) * STUD_SPACING_LDU
            local_z = (row + 0.5) * STUD_SPACING_LDU

            # Anti-stud on bottom
            anti_local = Point3D(local_x, 0.0, local_z)
            connectors.append(Connector(
                connector_id=f"anti_stud_{col}_{row}",
                connector_type=ConnectorType.ANTI_STUD,
                position=pose.transform_point(anti_local),
                normal=pose.transform_vector(anti_n_local),
            ))

            # Stud at high end only
            if row >= dims.studs_z - flat_rows:
                stud_local = Point3D(local_x, dims.height_ldu, local_z)
                connectors.append(Connector(
                    connector_id=f"stud_{col}_{row}",
                    connector_type=ConnectorType.STUD,
                    position=pose.transform_point(stud_local),
                    normal=pose.transform_vector(stud_n_local),
                ))

    return connectors


# ---------------------------------------------------------------------------
# Technic connector generation
# ---------------------------------------------------------------------------

def generate_technic_connectors(part: PartMetadata, pose: Pose) -> List[Connector]:
    """
    Generate world-space connectors for a TECHNIC part.

    A Technic brick has three connector families:

    1. Studs (top face) — same as a regular brick.
    2. Anti-studs (bottom face) — same as a regular brick.
    3. TECHNIC_HOLE — one connector per hole position, placed at the
       horizontal centre of the brick body, facing along the hole axis.
       Each hole produces *two* TECHNIC_HOLE connectors (one for each
       opening) so that a pin can be inserted from either side.
    """
    dims = part.dimensions
    tg = part.technic_geometry
    connectors: List[Connector] = []

    stud_n_local = _stud_normal_local()
    anti_n_local = _anti_stud_normal_local()
    mid_y = dims.height_ldu / 2.0  # vertical centre of the brick body

    # Determine hole axis normal in local space
    if tg is not None and tg.hole_axis == "z":
        pos_normal_local = Vector3D(0.0, 0.0, 1.0)
        neg_normal_local = Vector3D(0.0, 0.0, -1.0)
    else:
        pos_normal_local = Vector3D(1.0, 0.0, 0.0)
        neg_normal_local = Vector3D(-1.0, 0.0, 0.0)

    hole_set = set(tg.hole_positions) if tg is not None else set()

    for col in range(dims.studs_x):
        for row in range(dims.studs_z):
            local_x = (col + 0.5) * STUD_SPACING_LDU
            local_z = (row + 0.5) * STUD_SPACING_LDU

            # Stud (top)
            stud_local = Point3D(local_x, dims.height_ldu, local_z)
            connectors.append(Connector(
                connector_id=f"stud_{col}_{row}",
                connector_type=ConnectorType.STUD,
                position=pose.transform_point(stud_local),
                normal=pose.transform_vector(stud_n_local),
            ))

            # Anti-stud (bottom)
            anti_local = Point3D(local_x, 0.0, local_z)
            connectors.append(Connector(
                connector_id=f"anti_stud_{col}_{row}",
                connector_type=ConnectorType.ANTI_STUD,
                position=pose.transform_point(anti_local),
                normal=pose.transform_vector(anti_n_local),
            ))

            # Technic holes (two openings per hole position)
            if (col, row) in hole_set:
                hole_centre = Point3D(local_x, mid_y, local_z)
                hole_world = pose.transform_point(hole_centre)
                connectors.append(Connector(
                    connector_id=f"hole_{col}_{row}_pos",
                    connector_type=ConnectorType.TECHNIC_HOLE,
                    position=hole_world,
                    normal=pose.transform_vector(pos_normal_local),
                ))
                connectors.append(Connector(
                    connector_id=f"hole_{col}_{row}_neg",
                    connector_type=ConnectorType.TECHNIC_HOLE,
                    position=hole_world,
                    normal=pose.transform_vector(neg_normal_local),
                ))

    return connectors
