"""
Connection rules and validation for the LEGO geometry engine.

Phase A rules (STUD ↔ ANTI_STUD)
---------------------------------
1. Only STUD ↔ ANTI_STUD pairings are legal.
2. Connector positions must be within CONNECTION_POSITION_TOLERANCE.
3. Normals must be anti-parallel (dot ≈ −1): stud points +Y, anti-stud −Y.
4. Both connectors must be FREE.

Phase B additions (Technic connectors)
---------------------------------------
TECHNIC_PIN  ↔ TECHNIC_HOLE
TECHNIC_AXLE ↔ TECHNIC_AXLE_HOLE

Rules are identical except the *normal orientation* check uses parallel
normals (|dot| ≈ 1) rather than anti-parallel: both connectors' normals
point along the shared axle axis.

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

# ---------------------------------------------------------------------------
# Connector family helpers
# ---------------------------------------------------------------------------

_TECHNIC_TYPES = frozenset({
    ConnectorType.TECHNIC_PIN,
    ConnectorType.TECHNIC_HOLE,
    ConnectorType.TECHNIC_AXLE,
    ConnectorType.TECHNIC_AXLE_HOLE,
})

# Legal mating pairs (order-insensitive — both orderings stored for O(1) lookup)
_COMPATIBLE_PAIRS: frozenset[frozenset[ConnectorType]] = frozenset({
    frozenset({ConnectorType.STUD,         ConnectorType.ANTI_STUD}),
    frozenset({ConnectorType.TECHNIC_PIN,  ConnectorType.TECHNIC_HOLE}),
    frozenset({ConnectorType.TECHNIC_AXLE, ConnectorType.TECHNIC_AXLE_HOLE}),
})


def types_are_compatible(a: ConnectorType, b: ConnectorType) -> bool:
    return frozenset({a, b}) in _COMPATIBLE_PAIRS


def _is_technic_pair(a: ConnectorType, b: ConnectorType) -> bool:
    """Return True if both connector types belong to the Technic family."""
    return a in _TECHNIC_TYPES and b in _TECHNIC_TYPES


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
        Verify connector normal orientation.

        - STUD ↔ ANTI_STUD:           normals must be anti-parallel (dot ≈ −1).
        - Technic pairs:               normals must be co-axial (|dot| ≈ 1),
                                       i.e., parallel or anti-parallel along the
                                       shared hole axis.
        """
        n_a = (a_world_normal if a_world_normal is not None else a.normal).normalize()
        n_b = (b_world_normal if b_world_normal is not None else b.normal).normalize()
        dot = n_a.dot(n_b)

        if _is_technic_pair(a.connector_type, b.connector_type):
            # Allow either parallel (pin entering from this side) or
            # anti-parallel (pin entering from opposite side).
            if abs(dot) < self.normal_tolerance:
                return _fail(
                    f"Technic normals are not co-axial: |dot|={abs(dot):.4f} "
                    f"(need ≥ {self.normal_tolerance})."
                )
            return _OK

        # Standard stud ↔ anti-stud: must be anti-parallel
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

        _MALE = frozenset({ConnectorType.STUD, ConnectorType.TECHNIC_PIN, ConnectorType.TECHNIC_AXLE})
        stud = a if a.connector_type in _MALE else b
        anti = b if b.connector_type not in _MALE else a
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

        # Orientation score:
        # - Anti-parallel (stud/anti-stud): 1 at dot=-1, 0 at dot=-tolerance
        # - Co-axial (Technic): 1 at |dot|=1, 0 at |dot|=tolerance
        if _is_technic_pair(a.connector_type, b.connector_type):
            ori_score = max(0.0, (abs(dot) - self.normal_tolerance) / (1.0 - self.normal_tolerance))
        else:
            ori_score = max(0.0, (-dot - self.normal_tolerance) / (1.0 - self.normal_tolerance))

        return pos_score * ori_score


# ---------------------------------------------------------------------------
# Module-level default instance
# ---------------------------------------------------------------------------

#: Shared default rules object — use directly for simple validation.
DEFAULT_RULES = ConnectionRules()
