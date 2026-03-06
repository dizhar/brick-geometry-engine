"""
Connection rules and validation for the LEGO geometry engine.

Phase A rules
-------------
1. Only STUD ↔ ANTI_STUD pairings are legal.
2. The connectors must be spatially aligned:
   - Their mating points must be within POSITION_TOLERANCE_LDU of each other.
3. Their normals must be anti-parallel (dot product ≈ −1):
   - A stud's normal (+Y) must point directly into the anti-stud's normal (−Y).
4. Both connectors must be FREE.

All validation methods return a ValidationResult so callers can surface
meaningful error messages without catching exceptions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

from .connector_model import Connector, ConnectorPair, ConnectorType, ConnectorState
from ..core.geometry import Point3D, Vector3D
from ..core.constants import POSITION_TOLERANCE_LDU


# ---------------------------------------------------------------------------
# ValidationResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    reason: str = ""

    def __bool__(self) -> bool:
        return self.valid

    def __repr__(self) -> str:
        tag = "OK" if self.valid else "FAIL"
        return f"ValidationResult({tag}: {self.reason!r})" if self.reason else f"ValidationResult({tag})"


_OK = ValidationResult(True)


def _fail(reason: str) -> ValidationResult:
    return ValidationResult(False, reason)


# ---------------------------------------------------------------------------
# Compatibility matrix
# ---------------------------------------------------------------------------

# Maps (connector_type_a, connector_type_b) → True if the pairing is legal.
# Phase A: only STUD ↔ ANTI_STUD.
_COMPATIBILITY: dict[tuple[ConnectorType, ConnectorType], bool] = {
    (ConnectorType.STUD, ConnectorType.ANTI_STUD): True,
    (ConnectorType.ANTI_STUD, ConnectorType.STUD): True,
    (ConnectorType.STUD, ConnectorType.STUD): False,
    (ConnectorType.ANTI_STUD, ConnectorType.ANTI_STUD): False,
}


def types_are_compatible(a: ConnectorType, b: ConnectorType) -> bool:
    return _COMPATIBILITY.get((a, b), False)


# ---------------------------------------------------------------------------
# Tolerance constants
# ---------------------------------------------------------------------------

# Maximum distance between mating points for a valid connection.
CONNECTION_POSITION_TOLERANCE: float = POSITION_TOLERANCE_LDU * 10  # 0.1 LDU

# Minimum |dot(normal_a, normal_b)| for anti-parallel check.
# cos(170°) ≈ −0.985  →  we require dot < −0.98.
CONNECTION_NORMAL_TOLERANCE: float = 0.98


# ---------------------------------------------------------------------------
# ConnectionRules
# ---------------------------------------------------------------------------

class ConnectionRules:
    """
    Stateless validator for connector pairings.

    All methods are static/class-level — instantiate only if you want to
    override tolerance values at runtime.
    """

    def __init__(
        self,
        position_tolerance: float = CONNECTION_POSITION_TOLERANCE,
        normal_tolerance: float = CONNECTION_NORMAL_TOLERANCE,
    ) -> None:
        self.position_tolerance = position_tolerance
        self.normal_tolerance = normal_tolerance

    # --- individual checks ---

    def check_type_compatibility(
        self, a: Connector, b: Connector
    ) -> ValidationResult:
        """Verify that the connector types can mate."""
        if not types_are_compatible(a.connector_type, b.connector_type):
            return _fail(
                f"Incompatible types: {a.connector_type.name} cannot mate "
                f"with {b.connector_type.name}."
            )
        return _OK

    def check_availability(
        self, a: Connector, b: Connector
    ) -> ValidationResult:
        """Verify that both connectors are FREE."""
        if not a.is_free:
            return _fail(f"Connector {a.connector_id!r} is already occupied.")
        if not b.is_free:
            return _fail(f"Connector {b.connector_id!r} is already occupied.")
        return _OK

    def check_alignment(
        self,
        a: Connector,
        b: Connector,
        a_world_pos: Optional[Point3D] = None,
        b_world_pos: Optional[Point3D] = None,
    ) -> ValidationResult:
        """
        Verify spatial alignment of connector base positions.

        Alignment is checked at the connector's position (the base of the stud /
        the opening of the anti-stud), not the stud tip.  This matches the LEGO
        geometry where the stud protrudes *into* the anti-stud tube so the two
        base centres coincide when properly mated.

        If *a_world_pos* / *b_world_pos* are provided they override the
        connector's own position (used when connectors have been transformed
        to world space by the assembly engine).
        """
        pos_a = a_world_pos if a_world_pos is not None else a.position
        pos_b = b_world_pos if b_world_pos is not None else b.position
        dist = pos_a.distance_to(pos_b)
        if dist > self.position_tolerance:
            return _fail(
                f"Mating points are {dist:.4f} LDU apart "
                f"(tolerance {self.position_tolerance} LDU)."
            )
        return _OK

    def check_normal_orientation(
        self,
        a: Connector,
        b: Connector,
        a_world_normal: Optional[Vector3D] = None,
        b_world_normal: Optional[Vector3D] = None,
    ) -> ValidationResult:
        """
        Verify that the normals are anti-parallel (pointing toward each other).
        """
        n_a = (a_world_normal if a_world_normal is not None else a.normal).normalize()
        n_b = (b_world_normal if b_world_normal is not None else b.normal).normalize()
        dot = n_a.dot(n_b)
        if dot > -self.normal_tolerance:
            angle_deg = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
            return _fail(
                f"Normals are not anti-parallel: dot={dot:.4f}, "
                f"angle={angle_deg:.1f}° (need ≥ {math.degrees(math.acos(-self.normal_tolerance)):.1f}°)."
            )
        return _OK

    # --- combined validation ---

    def validate(
        self,
        a: Connector,
        b: Connector,
        a_world_pos: Optional[Point3D] = None,
        b_world_pos: Optional[Point3D] = None,
        a_world_normal: Optional[Vector3D] = None,
        b_world_normal: Optional[Vector3D] = None,
    ) -> ValidationResult:
        """
        Run all Phase-A connection checks in order.

        Returns the first failing result, or _OK if all pass.
        """
        for check in (
            self.check_type_compatibility(a, b),
            self.check_availability(a, b),
            self.check_alignment(a, b, a_world_pos, b_world_pos),
            self.check_normal_orientation(a, b, a_world_normal, b_world_normal),
        ):
            if not check:
                return check
        return _OK

    def validate_batch(
        self,
        pairs: Sequence[tuple[Connector, Connector]],
    ) -> List[ValidationResult]:
        """Validate a list of (connector_a, connector_b) pairs in one call."""
        return [self.validate(a, b) for a, b in pairs]

    # --- connection formation ---

    def form_connection(
        self,
        a: Connector,
        b: Connector,
        a_world_pos: Optional[Point3D] = None,
        b_world_pos: Optional[Point3D] = None,
        a_world_normal: Optional[Vector3D] = None,
        b_world_normal: Optional[Vector3D] = None,
    ) -> ConnectorPair:
        """
        Validate and mutually occupy both connectors, returning a ConnectorPair.

        Raises ValueError if validation fails.
        """
        result = self.validate(a, b, a_world_pos, b_world_pos, a_world_normal, b_world_normal)
        if not result:
            raise ValueError(f"Cannot form connection: {result.reason}")

        stud = a if a.connector_type == ConnectorType.STUD else b
        anti = b if b.connector_type == ConnectorType.ANTI_STUD else a
        stud.occupy(anti)
        anti.occupy(stud)
        return ConnectorPair(stud=stud, anti_stud=anti)

    def break_connection(self, pair: ConnectorPair) -> None:
        """Release both connectors in a ConnectorPair."""
        pair.stud.release()
        pair.anti_stud.release()

    # --- scoring ---

    def connection_score(
        self,
        a: Connector,
        b: Connector,
        a_world_pos: Optional[Point3D] = None,
        b_world_pos: Optional[Point3D] = None,
        a_world_normal: Optional[Vector3D] = None,
        b_world_normal: Optional[Vector3D] = None,
    ) -> float:
        """
        Return a quality score in [0, 1] for a potential connection.

        0.0 = invalid pairing, 1.0 = perfect geometric alignment.
        Used by the placement engine to rank candidate connections.
        """
        if not self.check_type_compatibility(a, b) or not self.check_availability(a, b):
            return 0.0

        pos_a = a_world_pos if a_world_pos is not None else a.position
        pos_b = b_world_pos if b_world_pos is not None else b.position
        n_a = (a_world_normal if a_world_normal is not None else a.normal).normalize()
        n_b = (b_world_normal if b_world_normal is not None else b.normal).normalize()

        dist = pos_a.distance_to(pos_b)
        dot = n_a.dot(n_b)

        # Position score: 1 when perfectly aligned, 0 at tolerance boundary.
        pos_score = max(0.0, 1.0 - dist / self.position_tolerance)

        # Orientation score: 1 when perfectly anti-parallel (dot == -1).
        ori_score = max(0.0, (-dot - self.normal_tolerance) / (1.0 - self.normal_tolerance))

        return pos_score * ori_score


# ---------------------------------------------------------------------------
# Module-level default instance
# ---------------------------------------------------------------------------

#: Shared default rules object — use directly for simple validation.
DEFAULT_RULES = ConnectionRules()
