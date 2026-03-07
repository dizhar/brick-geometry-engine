"""
Connector model for the LEGO geometry engine.

A Connector is a mating point on a part — either a stud (male, on the top
face) or an anti-stud (female, on the bottom face / inner tube).

All positions and normals are expressed in the part's local coordinate system
using LDU.  The engine transforms them to world space when needed.

Phase A: only STUD and ANTI_STUD connector types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from ..core.geometry import Point3D, Vector3D
from ..core.constants import (
    STUD_DIAMETER_LDU,
    STUD_HEIGHT_LDU,
    ANTI_STUD_DIAMETER_LDU,
    POSITION_TOLERANCE_LDU,
)


# ---------------------------------------------------------------------------
# ConnectorType
# ---------------------------------------------------------------------------

class ConnectorType(Enum):
    STUD = auto()            # raised cylinder on top face (male)
    ANTI_STUD = auto()       # receiving tube on bottom face (female)
    # Phase B: Technic horizontal connectors
    TECHNIC_PIN = auto()     # cross-shaped pin tip (male, inserts into hole)
    TECHNIC_HOLE = auto()    # round axle hole in a beam/brick (female)
    TECHNIC_AXLE = auto()    # smooth cylindrical axle (male)
    TECHNIC_AXLE_HOLE = auto()  # axle-shaped hole (female)


# ---------------------------------------------------------------------------
# ConnectorState
# ---------------------------------------------------------------------------

class ConnectorState(Enum):
    FREE = auto()       # available for mating
    OCCUPIED = auto()   # already connected to another connector


# ---------------------------------------------------------------------------
# Connector
# ---------------------------------------------------------------------------

@dataclass
class Connector:
    """
    A single mating point on a LEGO part.

    Attributes
    ----------
    connector_id:
        Unique identifier within the owning part, e.g. "stud_0_0".
    connector_type:
        STUD or ANTI_STUD.
    position:
        Centre of the connector in part-local LDU coordinates.
        For a stud this is the centre of the stud's base circle.
        For an anti-stud this is the centre of the receiving tube opening.
    normal:
        Unit vector pointing *away from the part body* in the mating
        direction.  Studs point +Y; anti-studs point −Y.
    state:
        FREE or OCCUPIED.
    connected_to:
        Reference to the mated Connector (set by the assembly engine).
    """
    connector_id: str
    connector_type: ConnectorType
    position: Point3D
    normal: Vector3D
    state: ConnectorState = field(default=ConnectorState.FREE)
    connected_to: Optional["Connector"] = field(default=None, repr=False)

    # --- geometry helpers ---

    @property
    def diameter(self) -> float:
        """Outer diameter of this connector in LDU."""
        if self.connector_type == ConnectorType.STUD:
            return STUD_DIAMETER_LDU
        if self.connector_type in (ConnectorType.TECHNIC_PIN, ConnectorType.TECHNIC_HOLE):
            return STUD_DIAMETER_LDU        # pin OD matches stud OD
        if self.connector_type in (ConnectorType.TECHNIC_AXLE, ConnectorType.TECHNIC_AXLE_HOLE):
            return ANTI_STUD_DIAMETER_LDU   # axle slightly narrower
        return ANTI_STUD_DIAMETER_LDU

    @property
    def height(self) -> float:
        """
        Protrusion height in LDU.

        Studs protrude by STUD_HEIGHT_LDU above the part face.
        Technic connectors are flush (protrusion handled externally).
        Anti-studs / holes are recessed and return 0.
        """
        if self.connector_type == ConnectorType.STUD:
            return STUD_HEIGHT_LDU
        return 0.0

    def mating_point(self) -> Point3D:
        """
        The point at which this connector makes contact with its mate.

        For a stud: top of the stud cylinder.
        For an anti-stud: the opening face (same as position).
        """
        offset = self.normal * self.height
        return Point3D(
            self.position.x + offset.x,
            self.position.y + offset.y,
            self.position.z + offset.z,
        )

    # --- state helpers ---

    @property
    def is_free(self) -> bool:
        return self.state == ConnectorState.FREE

    def occupy(self, partner: "Connector") -> None:
        """Mark this connector as occupied by *partner*."""
        self.state = ConnectorState.OCCUPIED
        self.connected_to = partner

    def release(self) -> None:
        """Free this connector."""
        self.state = ConnectorState.FREE
        self.connected_to = None

    # --- comparison ---

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Connector):
            return NotImplemented
        return (
            self.connector_id == other.connector_id
            and self.connector_type == other.connector_type
            and self.position == other.position
            and self.normal == other.normal
        )

    def __hash__(self) -> int:
        return hash(self.connector_id)

    def __repr__(self) -> str:
        return (
            f"Connector({self.connector_id!r}, {self.connector_type.name}, "
            f"pos={self.position!r}, state={self.state.name})"
        )


# ---------------------------------------------------------------------------
# ConnectorPair
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConnectorPair:
    """
    A resolved mating between two connectors (one STUD, one ANTI_STUD).

    Immutable — created by the assembly engine when a connection is formed.
    """
    stud: Connector
    anti_stud: Connector

    _MALE_TYPES = frozenset({ConnectorType.STUD, ConnectorType.TECHNIC_PIN, ConnectorType.TECHNIC_AXLE})
    _FEMALE_TYPES = frozenset({ConnectorType.ANTI_STUD, ConnectorType.TECHNIC_HOLE, ConnectorType.TECHNIC_AXLE_HOLE})

    def __post_init__(self) -> None:
        if self.stud.connector_type not in ConnectorPair._MALE_TYPES:
            raise ValueError(
                f"'stud' field must be a male connector (STUD/TECHNIC_PIN/TECHNIC_AXLE), "
                f"got {self.stud.connector_type.name}."
            )
        if self.anti_stud.connector_type not in ConnectorPair._FEMALE_TYPES:
            raise ValueError(
                f"'anti_stud' field must be a female connector "
                f"(ANTI_STUD/TECHNIC_HOLE/TECHNIC_AXLE_HOLE), "
                f"got {self.anti_stud.connector_type.name}."
            )

    def __repr__(self) -> str:
        return f"ConnectorPair(stud={self.stud.connector_id!r}, anti_stud={self.anti_stud.connector_id!r})"
