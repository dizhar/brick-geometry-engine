"""
Stability analysis for the LEGO geometry engine (Phase C).

This module classifies every node in an ``Assembly`` according to whether it
is physically supported, and reports structural problems.

Support model
-------------
The analysis is based on three layered concepts:

1. **Grounded** — the part's world-space AABB bottom (min Y) is within
   *ground_tolerance* of *ground_y* (default 0 LDU).  These parts rest
   directly on the build surface and need no further justification.

2. **Supported** — the part is reachable from any grounded node through
   the assembly's bond graph (any connector type: stud, anti-stud, Technic).
   BFS propagates "support" through all bonds regardless of direction.

3. **Floating** — the part is neither grounded nor reachable from a grounded
   node.  Floating parts are structural errors: they have no physical anchor.

Additionally:

4. **Isolated** — the part has zero bonds.  Isolated parts that are *also*
   grounded are valid (a loose brick on a table); isolated parts that are
   *not* grounded are floating.

Limitations
-----------
This is a topological / graph-based analysis, not a physics simulation.
It does *not* model:
  - Cantilever loads or torque
  - Frictional contact between non-bonded parts
  - SNOT (Studs Not On Top) side-stacking stability

These are Phase D / simulation concerns.

Usage
-----
::

    from brick_geometry.analysis.stability import StabilityAnalyzer
    analyzer = StabilityAnalyzer()
    report = analyzer.analyse(assembly)
    if not report.is_stable:
        print(report.floating_nodes)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set

from ..assembly.assembly_graph import Assembly
from ..assembly.assembly_node import AssemblyNode
from ..collision.bounding_box import world_box
from ..core.constants import POSITION_TOLERANCE_LDU


# ---------------------------------------------------------------------------
# NodeStatus
# ---------------------------------------------------------------------------

class NodeStatus(Enum):
    """Classification of a single node's structural status."""
    GROUNDED   = auto()  # directly resting on ground plane
    SUPPORTED  = auto()  # reachable from a grounded node via bonds
    FLOATING   = auto()  # not connected to any grounded node
    ISOLATED   = auto()  # no bonds at all (may still be grounded)


# ---------------------------------------------------------------------------
# StabilityReport
# ---------------------------------------------------------------------------

@dataclass
class StabilityReport:
    """
    Result of a stability analysis run.

    Attributes
    ----------
    status_map:
        Maps ``instance_id → NodeStatus`` for every node in the assembly.
    grounded_nodes:
        Nodes whose world AABB base touches the ground plane.
    supported_nodes:
        Nodes reachable from a grounded node through the bond graph
        (includes the grounded nodes themselves).
    floating_nodes:
        Nodes not connected (even transitively) to any grounded node.
        These are structural errors.
    isolated_nodes:
        Nodes with no bonds whatsoever.
        Isolated *and* grounded → GROUNDED (physically valid, not bonded).
        Isolated *and not* grounded → FLOATING (structural error).
    is_stable:
        True when ``floating_nodes`` is empty.
    errors:
        One entry per floating node describing the problem.
    warnings:
        Advisory messages (e.g. isolated-but-grounded parts).
    ground_y:
        The Y level treated as the ground plane.
    """
    status_map: Dict[str, NodeStatus] = field(default_factory=dict)
    grounded_nodes: List[AssemblyNode] = field(default_factory=list)
    supported_nodes: List[AssemblyNode] = field(default_factory=list)
    floating_nodes: List[AssemblyNode] = field(default_factory=list)
    isolated_nodes: List[AssemblyNode] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    ground_y: float = 0.0

    @property
    def is_stable(self) -> bool:
        """True when no nodes are floating."""
        return len(self.floating_nodes) == 0

    # -----------------------------------------------------------------------
    # Convenience queries
    # -----------------------------------------------------------------------

    def node_status(self, instance_id: str) -> NodeStatus:
        """Return the status of a single node; raises KeyError if not found."""
        return self.status_map[instance_id]

    def floating_count(self) -> int:
        return len(self.floating_nodes)

    def grounded_count(self) -> int:
        return len(self.grounded_nodes)

    def __repr__(self) -> str:
        status = "STABLE" if self.is_stable else f"{self.floating_count()} floating"
        return (
            f"StabilityReport({status}, "
            f"grounded={self.grounded_count()}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)})"
        )


# ---------------------------------------------------------------------------
# StabilityAnalyzer
# ---------------------------------------------------------------------------

class StabilityAnalyzer:
    """
    Classifies assembly nodes as grounded, supported, or floating.

    Parameters
    ----------
    ground_y:
        Y coordinate of the ground plane in LDU (default 0.0).
    ground_tolerance:
        A node is considered grounded when its world-AABB min-Y is within
        this distance of *ground_y*.  Defaults to 10× ``POSITION_TOLERANCE_LDU``
        to absorb floating-point imprecision in placement.
    """

    def __init__(
        self,
        ground_y: float = 0.0,
        ground_tolerance: float = POSITION_TOLERANCE_LDU * 10,
    ) -> None:
        self.ground_y = ground_y
        self.ground_tolerance = ground_tolerance

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def analyse(self, assembly: Assembly) -> StabilityReport:
        """
        Run stability analysis on *assembly*.

        Returns
        -------
        StabilityReport
            Full classification of every node.
        """
        report = StabilityReport(ground_y=self.ground_y)

        if len(assembly) == 0:
            return report

        nodes = assembly.nodes()

        # --- Phase 1: identify grounded nodes --------------------------------
        grounded_ids: Set[str] = set()
        isolated_ids: Set[str] = set()

        for node in nodes:
            if self._is_grounded(node):
                grounded_ids.add(node.instance_id)
            if node.connection_count() == 0:
                isolated_ids.add(node.instance_id)

        # --- Phase 2: BFS to find all supported nodes ------------------------
        supported_ids = self._bfs_supported(assembly, grounded_ids)

        # --- Phase 3: classify every node ------------------------------------
        for node in nodes:
            nid = node.instance_id
            is_isolated = nid in isolated_ids

            if nid in grounded_ids:
                status = NodeStatus.GROUNDED
                report.grounded_nodes.append(node)
                report.supported_nodes.append(node)
                if is_isolated:
                    report.isolated_nodes.append(node)
                    report.warnings.append(
                        f"Node {nid[:8]}… ({node.part.part_id!r}) is grounded "
                        f"but has no bonds — it will fall if nudged."
                    )

            elif nid in supported_ids:
                status = NodeStatus.SUPPORTED
                report.supported_nodes.append(node)
                if is_isolated:
                    # Shouldn't happen (supported requires at least one bond),
                    # but guard defensively.
                    report.isolated_nodes.append(node)

            else:
                # Not grounded and not reachable from ground → floating
                if is_isolated:
                    status = NodeStatus.ISOLATED
                    report.isolated_nodes.append(node)
                else:
                    status = NodeStatus.FLOATING
                report.floating_nodes.append(node)
                report.errors.append(
                    f"Node {nid[:8]}… ({node.part.part_id!r}) at "
                    f"y={node.pose.position.y:.1f} LDU is floating — "
                    f"not connected to any grounded part."
                )

            report.status_map[nid] = status

        # --- Phase 4: floating component summary ------------------------------
        # Group floating nodes by connected component for better diagnostics.
        floating_set = {n.instance_id for n in report.floating_nodes}
        if floating_set:
            comps = assembly.connected_components()
            for comp in comps:
                comp_ids = {n.instance_id for n in comp}
                if comp_ids.issubset(floating_set) and len(comp) > 1:
                    rep_id = comp[0].instance_id[:8]
                    report.warnings.append(
                        f"Entire connected component of {len(comp)} parts "
                        f"(starting at {rep_id}…) is floating with no ground connection."
                    )

        return report

    def is_node_grounded(self, node: AssemblyNode) -> bool:
        """Return True if *node* directly touches the ground plane."""
        return self._is_grounded(node)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _is_grounded(self, node: AssemblyNode) -> bool:
        """
        A node is grounded when the bottom of its world AABB is within
        *ground_tolerance* of *ground_y*.
        """
        box = world_box(node.part, node.pose)
        return abs(box.min_point.y - self.ground_y) <= self.ground_tolerance

    @staticmethod
    def _bfs_supported(
        assembly: Assembly, grounded_ids: Set[str]
    ) -> Set[str]:
        """
        BFS from all grounded nodes through the bond graph.

        Returns the set of all reachable instance_ids (including the
        grounded seeds themselves).
        """
        visited: Set[str] = set(grounded_ids)
        queue: deque[str] = deque(grounded_ids)

        while queue:
            current_id = queue.popleft()
            for neighbour in assembly.neighbours(current_id):
                nid = neighbour.instance_id
                if nid not in visited:
                    visited.add(nid)
                    queue.append(nid)

        return visited
