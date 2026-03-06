"""
Placement engine — suggests and validates part placements within an Assembly.

The engine answers questions like:
  "Where can I place a 2×4 brick such that it connects to this node?"

Phase A strategy
----------------
For each free ANTI_STUD connector on an existing node (the 'anchor'), the
engine computes the pose that would bring a candidate part's STUD connector
into perfect alignment.  It then validates the placement for collisions and
any additional connector bonds that form naturally.

PlacementSuggestion
    A fully-resolved candidate: part + pose + the primary connector pair
    that was used to derive the pose + a quality score.

PlacementEngine
    Stateless helper that operates on an Assembly.  All methods are
    deterministic given the same assembly state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..core.geometry import Point3D, Vector3D
from ..core.transforms import Pose, Rotation
from ..parts.part_metadata import PartMetadata
from ..connectors.connector_model import Connector, ConnectorType
from ..connectors.connector_rules import ConnectionRules, DEFAULT_RULES, ValidationResult
from ..collision.collision_detection import CollisionDetector
from ..collision.bounding_box import world_box
from .assembly_node import AssemblyNode, generate_connectors
from .assembly_graph import Assembly


# ---------------------------------------------------------------------------
# PlacementSuggestion
# ---------------------------------------------------------------------------

@dataclass
class PlacementSuggestion:
    """
    A candidate placement for a part in the assembly.

    Attributes
    ----------
    part : PartMetadata
        The part to be placed.
    pose : Pose
        The world-space pose that aligns *anchor_connector* with
        *candidate_connector*.
    anchor_node_id : str
        The existing node whose connector is being mated.
    anchor_connector_id : str
        The free connector on the anchor node.
    candidate_connector_id : str
        The connector on the candidate part that mates with the anchor.
    score : float
        Quality score in [0, 1].  Higher is better.
    extra_bonds : int
        Number of *additional* connector bonds (beyond the primary one)
        that would form if the part were placed at this pose.
    """
    part: PartMetadata
    pose: Pose
    anchor_node_id: str
    anchor_connector_id: str
    candidate_connector_id: str
    score: float = 1.0
    extra_bonds: int = 0

    def __repr__(self) -> str:
        return (
            f"PlacementSuggestion("
            f"part={self.part.part_id!r}, "
            f"anchor={self.anchor_connector_id!r}→{self.candidate_connector_id!r}, "
            f"score={self.score:.3f}, extra_bonds={self.extra_bonds})"
        )


# ---------------------------------------------------------------------------
# Pose derivation
# ---------------------------------------------------------------------------

# All 90° rotations of a part around the Y axis (the four horizontal
# orientations a Phase-A part can have).
_Y_ROTATIONS: List[Rotation] = [
    Rotation.from_axis_angle_90("y", steps) for steps in range(4)
]


def _pose_to_align_stud_to_anti_stud(
    stud_pos_world: Point3D,
    stud_normal_world: Vector3D,
    anti_stud_pos_world: Point3D,
    anti_stud_normal_world: Vector3D,
    candidate_stud_local: Point3D,
    rotation: Rotation,
) -> Pose:
    """
    Compute the world pose for the candidate part so that its stud (in local
    space at *candidate_stud_local*) reaches *anti_stud_pos_world*.

    Steps
    -----
    1. Apply *rotation* to the candidate's local stud position.
    2. Translate so the rotated stud position coincides with the anti-stud's
       mating point (which is the anti-stud position itself for phase A).
    """
    rotated_local = rotation.apply_point(candidate_stud_local)
    translation = Vector3D(
        anti_stud_pos_world.x - rotated_local.x,
        anti_stud_pos_world.y - rotated_local.y,
        anti_stud_pos_world.z - rotated_local.z,
    )
    origin = Point3D(translation.x, translation.y, translation.z)
    return Pose(position=origin, rotation=rotation)


# ---------------------------------------------------------------------------
# PlacementEngine
# ---------------------------------------------------------------------------

class PlacementEngine:
    """
    Suggests valid placements for new parts in an Assembly.

    Parameters
    ----------
    assembly : Assembly
        The assembly to place parts into.
    rules : ConnectionRules
        Connection validation rules (defaults to DEFAULT_RULES).
    """

    def __init__(
        self,
        assembly: Assembly,
        rules: ConnectionRules = DEFAULT_RULES,
    ) -> None:
        self._assembly = assembly
        self._rules = rules

    # -----------------------------------------------------------------------
    # Primary API
    # -----------------------------------------------------------------------

    def suggest_placements(
        self,
        part: PartMetadata,
        anchor_node_id: Optional[str] = None,
        max_suggestions: int = 50,
    ) -> List[PlacementSuggestion]:
        """
        Return a ranked list of valid placements for *part*.

        Parameters
        ----------
        anchor_node_id:
            When given, only connectors on that node are used as anchors.
            When None, all free connectors in the assembly are considered.
        max_suggestions:
            Cap on returned suggestions (highest-scoring first).
        """
        suggestions: List[PlacementSuggestion] = []

        anchor_nodes = (
            [self._assembly.get_node(anchor_node_id)]
            if anchor_node_id
            else self._assembly.nodes()
        )

        for anchor_node in anchor_nodes:
            for anchor_conn in anchor_node.free_connectors():
                # Anchor must be a STUD — we place the new part ON TOP of it
                if anchor_conn.connector_type != ConnectorType.STUD:
                    continue

                new_suggestions = self._suggestions_for_anchor(
                    part, anchor_node, anchor_conn
                )
                suggestions.extend(new_suggestions)

        suggestions.sort(key=lambda s: (s.extra_bonds, s.score), reverse=True)
        return suggestions[:max_suggestions]

    def find_best_placement(
        self,
        part: PartMetadata,
        anchor_node_id: Optional[str] = None,
    ) -> Optional[PlacementSuggestion]:
        """Return the single best placement, or None if none is valid."""
        results = self.suggest_placements(part, anchor_node_id, max_suggestions=1)
        return results[0] if results else None

    def commit_placement(self, suggestion: PlacementSuggestion) -> AssemblyNode:
        """
        Place the part described by *suggestion* into the assembly and
        form the primary connector bond.

        Returns the new AssemblyNode.
        """
        new_node = self._assembly.place_part(
            suggestion.part,
            suggestion.pose,
            check_collision=True,
        )
        # Form the primary bond
        self._assembly.connect(
            suggestion.anchor_node_id,
            suggestion.anchor_connector_id,
            new_node.instance_id,
            suggestion.candidate_connector_id,
        )
        # Form any additional bonds that are in tolerance
        self._form_extra_bonds(new_node)
        return new_node

    # -----------------------------------------------------------------------
    # Collision-only check (no bonding)
    # -----------------------------------------------------------------------

    def is_placement_valid(self, part: PartMetadata, pose: Pose) -> bool:
        """
        Return True if placing *part* at *pose* would not collide with any
        existing part in the assembly.
        """
        collisions = self._assembly._collision.check_against_all(
            "__probe__", part, pose
        )
        return len(collisions) == 0

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _suggestions_for_anchor(
        self,
        part: PartMetadata,
        anchor_node: AssemblyNode,
        anchor_conn: Connector,
    ) -> List[PlacementSuggestion]:
        """
        For a single anchor STUD connector, try every anti-stud on *part*
        across all four Y-axis rotations.
        """
        suggestions: List[PlacementSuggestion] = []

        # Generate local-space connectors for the candidate part (pose=identity)
        local_connectors = generate_connectors(part, Pose.identity())
        anti_stud_locals = [c for c in local_connectors if c.connector_type == ConnectorType.ANTI_STUD]

        for rotation in _Y_ROTATIONS:
            for anti_local in anti_stud_locals:
                # Derive pose: place candidate so its anti-stud base aligns with anchor stud base
                pose = _pose_to_align_stud_to_anti_stud(
                    stud_pos_world=anti_local.position,
                    stud_normal_world=anti_local.normal,
                    anti_stud_pos_world=anchor_conn.position,
                    anti_stud_normal_world=anchor_conn.normal,
                    candidate_stud_local=anti_local.position,
                    rotation=rotation,
                )

                # Check the anti-stud normal is anti-parallel to the anchor stud normal
                rotated_normal = rotation.apply(anti_local.normal)
                result = self._rules.check_normal_orientation(
                    anti_local, anchor_conn,
                    a_world_normal=rotated_normal,
                    b_world_normal=anchor_conn.normal,
                )
                if not result:
                    continue

                # Collision check
                if not self.is_placement_valid(part, pose):
                    continue

                # Count extra bonds
                world_conns = generate_connectors(part, pose)
                extra = self._count_extra_bonds(world_conns, anti_local.connector_id, anchor_node)

                suggestions.append(PlacementSuggestion(
                    part=part,
                    pose=pose,
                    anchor_node_id=anchor_node.instance_id,
                    anchor_connector_id=anchor_conn.connector_id,
                    candidate_connector_id=anti_local.connector_id,
                    score=1.0,
                    extra_bonds=extra,
                ))

        return suggestions

    def _count_extra_bonds(
        self,
        candidate_world_connectors: List[Connector],
        primary_anti_stud_id: str,
        anchor_node: AssemblyNode,
    ) -> int:
        """
        Count additional connector bonds that would form between *candidate*
        and *anchor_node* (excluding the primary bond already planned).
        """
        count = 0
        for cand_conn in candidate_world_connectors:
            if cand_conn.connector_id == primary_anti_stud_id:
                continue
            if cand_conn.connector_type != ConnectorType.ANTI_STUD:
                continue
            for anchor_free in anchor_node.free_connectors():
                if anchor_free.connector_type != ConnectorType.STUD:
                    continue
                result = self._rules.check_alignment(cand_conn, anchor_free)
                if result:
                    n_result = self._rules.check_normal_orientation(cand_conn, anchor_free)
                    if n_result:
                        count += 1
        return count

    def _form_extra_bonds(self, new_node: AssemblyNode) -> None:
        """
        After placing *new_node*, form all additional connector bonds that
        are geometrically valid with any existing node.
        """
        for existing_node in self._assembly.nodes():
            if existing_node.instance_id == new_node.instance_id:
                continue
            for new_conn in new_node.free_connectors():
                if new_conn.connector_type != ConnectorType.ANTI_STUD:
                    continue
                for exist_conn in existing_node.free_connectors():
                    if exist_conn.connector_type != ConnectorType.STUD:
                        continue
                    result = self._rules.validate(new_conn, exist_conn)
                    if result:
                        try:
                            self._assembly.connect(
                                existing_node.instance_id,
                                exist_conn.connector_id,
                                new_node.instance_id,
                                new_conn.connector_id,
                            )
                        except ValueError:
                            pass  # already occupied by the time we get here
