"""
Assembly graph — the top-level container for a LEGO build.

The graph is a multigraph: nodes are AssemblyNode instances (placed parts),
edges are ConnectorPairs (STUD↔ANTI_STUD bonds).  Multiple edges between
the same pair of nodes are allowed (e.g. a 2×4 brick on a 2×4 plate shares
8 connector bonds).

Responsibilities
----------------
- Place and remove parts (with collision gating)
- Form and break connector bonds
- Graph traversal (BFS/DFS, connectivity)
- Assembly-level validation
"""

from __future__ import annotations

import uuid
from collections import deque
from typing import Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

from ..core.transforms import Pose
from ..parts.part_metadata import PartMetadata
from ..connectors.connector_model import Connector, ConnectorPair, ConnectorType
from ..connectors.connector_rules import ConnectionRules, DEFAULT_RULES
from ..collision.collision_detection import CollisionDetector
from .assembly_node import AssemblyNode


# ---------------------------------------------------------------------------
# Bond record (internal edge)
# ---------------------------------------------------------------------------

class _Bond:
    """Internal edge between two nodes."""
    __slots__ = ("bond_id", "node_a_id", "node_b_id", "pair")

    def __init__(self, node_a_id: str, node_b_id: str, pair: ConnectorPair) -> None:
        self.bond_id: str = str(uuid.uuid4())
        self.node_a_id = node_a_id
        self.node_b_id = node_b_id
        self.pair = pair

    def other(self, node_id: str) -> str:
        return self.node_b_id if node_id == self.node_a_id else self.node_a_id


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------

class ValidationReport:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def __repr__(self) -> str:
        status = "VALID" if self.is_valid else f"{len(self.errors)} error(s)"
        return f"ValidationReport({status}, {len(self.warnings)} warning(s))"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

class Assembly:
    """
    A directed multigraph of placed LEGO parts.

    Parameters
    ----------
    name : str
        Human-readable label for this assembly.
    rules : ConnectionRules
        Connection validation rules (defaults to DEFAULT_RULES).
    """

    def __init__(
        self,
        name: str = "assembly",
        rules: ConnectionRules = DEFAULT_RULES,
    ) -> None:
        self.name = name
        self._rules = rules
        self._nodes: Dict[str, AssemblyNode] = {}
        self._bonds: Dict[str, _Bond] = {}           # bond_id → _Bond
        self._node_bonds: Dict[str, Set[str]] = {}   # instance_id → {bond_id}
        self._collision = CollisionDetector()

    # -----------------------------------------------------------------------
    # Node management
    # -----------------------------------------------------------------------

    def place_part(
        self,
        part: PartMetadata,
        pose: Pose,
        instance_id: Optional[str] = None,
        check_collision: bool = True,
    ) -> AssemblyNode:
        """
        Place *part* at *pose* and add it to the assembly.

        Parameters
        ----------
        check_collision:
            When True (default), raises ValueError if the new part overlaps
            any existing part.

        Returns
        -------
        AssemblyNode
            The newly created node.
        """
        iid = instance_id or str(uuid.uuid4())
        if iid in self._nodes:
            raise ValueError(f"instance_id {iid!r} is already in this assembly.")

        if check_collision:
            hits = self._collision.check_against_all(iid, part, pose)
            if hits:
                others = ", ".join(h.id_b for h in hits)
                raise ValueError(
                    f"Cannot place {part.part_id!r} at {pose.position}: "
                    f"collides with [{others}]."
                )

        node = AssemblyNode(part=part, pose=pose, instance_id=iid)
        self._nodes[iid] = node
        self._node_bonds[iid] = set()
        self._collision.register(iid, part, pose)
        return node

    def remove_part(self, instance_id: str) -> AssemblyNode:
        """
        Remove a node and all its bonds from the assembly.

        Returns the removed AssemblyNode.
        """
        node = self._get_node(instance_id)

        # Break all bonds first
        for bond_id in list(self._node_bonds[instance_id]):
            self._break_bond(bond_id)

        del self._nodes[instance_id]
        del self._node_bonds[instance_id]
        self._collision.unregister(instance_id)
        return node

    def get_node(self, instance_id: str) -> AssemblyNode:
        return self._get_node(instance_id)

    def nodes(self) -> List[AssemblyNode]:
        return list(self._nodes.values())

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, instance_id: str) -> bool:
        return instance_id in self._nodes

    # -----------------------------------------------------------------------
    # Bond management
    # -----------------------------------------------------------------------

    def connect(
        self,
        node_a_id: str,
        connector_a_id: str,
        node_b_id: str,
        connector_b_id: str,
    ) -> ConnectorPair:
        """
        Form a connector bond between two nodes.

        Returns the resulting ConnectorPair.
        Raises ValueError if the connection is geometrically invalid.
        """
        node_a = self._get_node(node_a_id)
        node_b = self._get_node(node_b_id)
        conn_a = node_a.get_connector(connector_a_id)
        conn_b = node_b.get_connector(connector_b_id)

        pair = self._rules.form_connection(conn_a, conn_b)

        bond = _Bond(node_a_id, node_b_id, pair)
        self._bonds[bond.bond_id] = bond
        self._node_bonds[node_a_id].add(bond.bond_id)
        self._node_bonds[node_b_id].add(bond.bond_id)
        node_a.add_connection(bond.bond_id, pair)
        node_b.add_connection(bond.bond_id, pair)
        return pair

    def disconnect(self, bond_id: str) -> None:
        """Break the bond identified by *bond_id*."""
        if bond_id not in self._bonds:
            raise KeyError(f"Bond {bond_id!r} not found in assembly.")
        self._break_bond(bond_id)

    def disconnect_nodes(self, node_a_id: str, node_b_id: str) -> int:
        """
        Break *all* bonds between two nodes.

        Returns the number of bonds removed.
        """
        to_remove = [
            bid for bid in self._node_bonds.get(node_a_id, set())
            if self._bonds[bid].other(node_a_id) == node_b_id
        ]
        for bid in to_remove:
            self._break_bond(bid)
        return len(to_remove)

    def bonds_between(self, node_a_id: str, node_b_id: str) -> List[_Bond]:
        return [
            self._bonds[bid]
            for bid in self._node_bonds.get(node_a_id, set())
            if self._bonds[bid].other(node_a_id) == node_b_id
        ]

    def bond_count(self) -> int:
        return len(self._bonds)

    # -----------------------------------------------------------------------
    # Graph traversal
    # -----------------------------------------------------------------------

    def neighbours(self, instance_id: str) -> List[AssemblyNode]:
        """Return all nodes directly connected to *instance_id*."""
        self._get_node(instance_id)
        seen: Set[str] = set()
        result: List[AssemblyNode] = []
        for bid in self._node_bonds.get(instance_id, set()):
            other_id = self._bonds[bid].other(instance_id)
            if other_id not in seen:
                seen.add(other_id)
                result.append(self._nodes[other_id])
        return result

    def bfs(self, start_id: str) -> Iterator[AssemblyNode]:
        """Yield nodes reachable from *start_id* in breadth-first order."""
        visited: Set[str] = {start_id}
        queue: deque[str] = deque([start_id])
        while queue:
            current = queue.popleft()
            yield self._nodes[current]
            for neighbour in self.neighbours(current):
                if neighbour.instance_id not in visited:
                    visited.add(neighbour.instance_id)
                    queue.append(neighbour.instance_id)

    def dfs(self, start_id: str) -> Iterator[AssemblyNode]:
        """Yield nodes reachable from *start_id* in depth-first order."""
        visited: Set[str] = set()
        stack: List[str] = [start_id]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            yield self._nodes[current]
            for neighbour in self.neighbours(current):
                if neighbour.instance_id not in visited:
                    stack.append(neighbour.instance_id)

    def connected_components(self) -> List[List[AssemblyNode]]:
        """Return a list of connected components (each a list of nodes)."""
        unvisited = set(self._nodes)
        components: List[List[AssemblyNode]] = []
        while unvisited:
            start = next(iter(unvisited))
            component = list(self.bfs(start))
            components.append(component)
            unvisited -= {n.instance_id for n in component}
        return components

    def is_fully_connected(self) -> bool:
        """Return True if all nodes form a single connected component."""
        if len(self._nodes) == 0:
            return True
        return len(self.connected_components()) == 1

    def find_path(
        self, start_id: str, end_id: str
    ) -> Optional[List[AssemblyNode]]:
        """
        Return the shortest path (BFS) from *start_id* to *end_id*, or None.
        """
        if start_id == end_id:
            return [self._nodes[start_id]]

        parent: Dict[str, Optional[str]] = {start_id: None}
        queue: deque[str] = deque([start_id])
        while queue:
            current = queue.popleft()
            if current == end_id:
                path: List[str] = []
                node = end_id
                while node is not None:
                    path.append(node)
                    node = parent[node]  # type: ignore[assignment]
                return [self._nodes[n] for n in reversed(path)]
            for neighbour in self.neighbours(current):
                nid = neighbour.instance_id
                if nid not in parent:
                    parent[nid] = current
                    queue.append(nid)
        return None

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate(self) -> ValidationReport:
        """
        Run integrity checks on the entire assembly.

        Checks:
        - No collision between any pair of parts.
        - All bonds reference connectors that are marked OCCUPIED.
        - No isolated nodes (warning only).
        """
        report = ValidationReport()

        # Collision check
        collisions = self._collision.check_all()
        for col in collisions:
            report.errors.append(
                f"Collision between {col.id_a!r} and {col.id_b!r}."
            )

        # Bond integrity
        for bond_id, bond in self._bonds.items():
            pair = bond.pair
            if pair.stud.is_free:
                report.errors.append(
                    f"Bond {bond_id}: stud connector {pair.stud.connector_id!r} "
                    f"is unexpectedly FREE."
                )
            if pair.anti_stud.is_free:
                report.errors.append(
                    f"Bond {bond_id}: anti-stud connector "
                    f"{pair.anti_stud.connector_id!r} is unexpectedly FREE."
                )

        # Isolated nodes
        if len(self._nodes) > 1:
            for component in self.connected_components():
                if len(component) == 1:
                    report.warnings.append(
                        f"Node {component[0].instance_id!r} "
                        f"({component[0].part.part_id!r}) is isolated."
                    )

        return report

    # -----------------------------------------------------------------------
    # Serialisation helpers
    # -----------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "bonds": [
                {
                    "bond_id": b.bond_id,
                    "node_a": b.node_a_id,
                    "node_b": b.node_b_id,
                    "stud_connector": b.pair.stud.connector_id,
                    "anti_stud_connector": b.pair.anti_stud.connector_id,
                }
                for b in self._bonds.values()
            ],
        }

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _get_node(self, instance_id: str) -> AssemblyNode:
        try:
            return self._nodes[instance_id]
        except KeyError:
            raise KeyError(f"Node {instance_id!r} not found in assembly.")

    def _break_bond(self, bond_id: str) -> None:
        bond = self._bonds.pop(bond_id)
        self._rules.break_connection(bond.pair)
        self._node_bonds[bond.node_a_id].discard(bond_id)
        self._node_bonds[bond.node_b_id].discard(bond_id)
        node_a = self._nodes.get(bond.node_a_id)
        node_b = self._nodes.get(bond.node_b_id)
        if node_a:
            node_a.remove_connection(bond_id)
        if node_b:
            node_b.remove_connection(bond_id)

    def __repr__(self) -> str:
        return (
            f"Assembly({self.name!r}, "
            f"{len(self._nodes)} nodes, "
            f"{len(self._bonds)} bonds)"
        )
