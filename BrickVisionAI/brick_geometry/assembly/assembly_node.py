"""
AssemblyNode — a single placed part instance inside an Assembly.

Each node owns:
  - a PartMetadata record (what part it is)
  - a Pose (where it sits in world space)
  - a list of Connectors in world space (generated from the part footprint)
  - a set of active ConnectorPairs linking it to neighbouring nodes
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from ..core.geometry import Point3D, Vector3D
from ..core.transforms import Pose
from ..core.constants import STUD_SPACING_LDU, PLATE_HEIGHT_LDU, BRICK_HEIGHT_LDU
from ..parts.part_metadata import PartCategory, PartMetadata
from ..connectors.connector_model import Connector, ConnectorPair, ConnectorType
from ..connectors.connector_generation import (
    generate_slope_connectors,
    generate_technic_connectors,
)


# ---------------------------------------------------------------------------
# Standard connector generation (BRICK / PLATE / TILE / OTHER)
# ---------------------------------------------------------------------------

def _generate_standard_connectors(part: PartMetadata, pose: Pose) -> List[Connector]:
    """Studs on top face, anti-studs on bottom face — all grid positions."""
    dims = part.dimensions
    connectors: List[Connector] = []
    stud_n = Vector3D(0.0, 1.0, 0.0)
    anti_n = Vector3D(0.0, -1.0, 0.0)

    for col in range(dims.studs_x):
        for row in range(dims.studs_z):
            local_x = (col + 0.5) * STUD_SPACING_LDU
            local_z = (row + 0.5) * STUD_SPACING_LDU

            stud_local = Point3D(local_x, dims.height_ldu, local_z)
            connectors.append(Connector(
                connector_id=f"stud_{col}_{row}",
                connector_type=ConnectorType.STUD,
                position=pose.transform_point(stud_local),
                normal=pose.transform_vector(stud_n),
            ))

            anti_local = Point3D(local_x, 0.0, local_z)
            connectors.append(Connector(
                connector_id=f"anti_stud_{col}_{row}",
                connector_type=ConnectorType.ANTI_STUD,
                position=pose.transform_point(anti_local),
                normal=pose.transform_vector(anti_n),
            ))

    return connectors


def generate_connectors(part: PartMetadata, pose: Pose) -> List[Connector]:
    """
    Generate world-space connectors for *part* placed at *pose*.

    Dispatches to the appropriate generator based on part category:
    - SLOPE   → generate_slope_connectors   (Phase B)
    - TECHNIC → generate_technic_connectors (Phase B)
    - All others → standard studs + anti-studs on a full grid

    Grid layout in local space (X, Z axes):
        col offset = (col + 0.5) × STUD_SPACING_LDU
        row offset = (row + 0.5) × STUD_SPACING_LDU
    """
    if part.category == PartCategory.SLOPE:
        return generate_slope_connectors(part, pose)
    if part.category == PartCategory.TECHNIC:
        return generate_technic_connectors(part, pose)
    return _generate_standard_connectors(part, pose)


# ---------------------------------------------------------------------------
# AssemblyNode
# ---------------------------------------------------------------------------

class AssemblyNode:
    """
    A placed instance of a LEGO part within an Assembly.

    Attributes
    ----------
    instance_id : str
        Unique ID within the assembly (auto-generated UUID if not provided).
    part : PartMetadata
        The part definition.
    pose : Pose
        World-space pose.
    connectors : List[Connector]
        World-space connectors (regenerated whenever pose changes).
    connections : Dict[str, ConnectorPair]
        Active bonds keyed by the partner node's instance_id.
        A node may have multiple simultaneous connections to the same
        neighbour (e.g. a 2×4 brick sitting on a 2×4 plate).
    """

    def __init__(
        self,
        part: PartMetadata,
        pose: Pose,
        instance_id: Optional[str] = None,
    ) -> None:
        self.instance_id: str = instance_id or str(uuid.uuid4())
        self.part: PartMetadata = part
        self._pose: Pose = pose
        self.connectors: List[Connector] = generate_connectors(part, pose)
        # keyed by an arbitrary bond_id so a node can hold multiple bonds
        self._connections: Dict[str, ConnectorPair] = {}
        # quick lookup: connector_id → ConnectorPair bond_id
        self._connector_bond: Dict[str, str] = {}

    # --- pose ---

    @property
    def pose(self) -> Pose:
        return self._pose

    @pose.setter
    def pose(self, new_pose: Pose) -> None:
        if self._connections:
            raise RuntimeError(
                "Cannot move a node that has active connections. "
                "Disconnect it first."
            )
        self._pose = new_pose
        self.connectors = generate_connectors(self.part, new_pose)

    # --- connector access ---

    def get_connector(self, connector_id: str) -> Connector:
        for c in self.connectors:
            if c.connector_id == connector_id:
                return c
        raise KeyError(f"Connector {connector_id!r} not found on node {self.instance_id!r}.")

    def free_connectors(self) -> List[Connector]:
        return [c for c in self.connectors if c.is_free]

    def occupied_connectors(self) -> List[Connector]:
        return [c for c in self.connectors if not c.is_free]

    # --- connection management ---

    def add_connection(self, bond_id: str, pair: ConnectorPair) -> None:
        self._connections[bond_id] = pair
        # Track which local connectors are involved
        if pair.stud in self.connectors:
            self._connector_bond[pair.stud.connector_id] = bond_id
        if pair.anti_stud in self.connectors:
            self._connector_bond[pair.anti_stud.connector_id] = bond_id

    def remove_connection(self, bond_id: str) -> ConnectorPair:
        pair = self._connections.pop(bond_id)
        self._connector_bond = {
            cid: bid for cid, bid in self._connector_bond.items() if bid != bond_id
        }
        return pair

    @property
    def connections(self) -> Dict[str, ConnectorPair]:
        return dict(self._connections)

    def is_connected_to(self, other_instance_id: str) -> bool:
        for pair in self._connections.values():
            stud_id = pair.stud.connector_id
            anti_id = pair.anti_stud.connector_id
            # Check if either connector in the pair belongs to the other node
            # (the assembly graph stores the bond on both nodes)
            _ = stud_id, anti_id  # used indirectly via the pair reference
        return other_instance_id in {
            bid.split(":")[0] for bid in self._connections
        }

    def connection_count(self) -> int:
        return len(self._connections)

    # --- serialisation ---

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "part_id": self.part.part_id,
            "position": self.pose.position.to_tuple(),
            "rotation_matrix": list(self.pose.rotation._mat),
        }

    # --- misc ---

    def clone(self, new_instance_id: Optional[str] = None) -> AssemblyNode:
        """Return a disconnected copy of this node with a fresh ID."""
        node = AssemblyNode(
            part=self.part,
            pose=self._pose,
            instance_id=new_instance_id or str(uuid.uuid4()),
        )
        return node

    def __repr__(self) -> str:
        return (
            f"AssemblyNode(id={self.instance_id[:8]}…, "
            f"part={self.part.part_id!r}, "
            f"connections={len(self._connections)})"
        )
