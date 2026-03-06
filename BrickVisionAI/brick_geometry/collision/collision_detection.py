"""
Collision detection for the LEGO geometry engine.

Phase A uses a two-phase AABB strategy:

  Broad phase  — spatial hash grid; quickly discards pairs that are too far
                 apart to ever overlap.
  Narrow phase — exact AABB intersection test on the surviving pairs.

The CollisionDetector is intentionally decoupled from the assembly graph so
that it can be used stand-alone (e.g. to validate a placement before
committing it) as well as called by the assembly engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

from ..core.geometry import BoundingBox, Point3D
from ..core.transforms import Pose
from ..core.constants import POSITION_TOLERANCE_LDU
from ..parts.part_metadata import PartMetadata
from .bounding_box import world_box, expanded_box


# ---------------------------------------------------------------------------
# CollisionResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CollisionResult:
    """Describes a detected collision between two placed parts."""
    id_a: str
    id_b: str
    box_a: BoundingBox
    box_b: BoundingBox

    @property
    def pair_key(self) -> FrozenSet[str]:
        return frozenset({self.id_a, self.id_b})

    def __repr__(self) -> str:
        return f"CollisionResult({self.id_a!r} ↔ {self.id_b!r})"


# ---------------------------------------------------------------------------
# PlacedPart  (lightweight record used internally)
# ---------------------------------------------------------------------------

@dataclass
class PlacedPart:
    """A part registered with the collision detector."""
    instance_id: str
    part: PartMetadata
    pose: Pose
    _cached_box: Optional[BoundingBox] = field(default=None, repr=False)

    def world_box(self) -> BoundingBox:
        if self._cached_box is None:
            self._cached_box = world_box(self.part, self.pose)
        return self._cached_box

    def invalidate_cache(self) -> None:
        self._cached_box = None


# ---------------------------------------------------------------------------
# Spatial hash grid (broad phase)
# ---------------------------------------------------------------------------

# Cell size chosen to be slightly larger than the largest common part
# (2×10 brick = 200 LDU wide) so that most parts fit in 1–4 cells.
_CELL_SIZE: float = 240.0

_CellKey = Tuple[int, int, int]


def _cell_keys_for_box(box: BoundingBox) -> Iterator[_CellKey]:
    """Yield all grid cell keys that *box* overlaps."""
    def _range(lo: float, hi: float) -> range:
        import math
        return range(math.floor(lo / _CELL_SIZE), math.floor(hi / _CELL_SIZE) + 1)

    for cx in _range(box.min_point.x, box.max_point.x):
        for cy in _range(box.min_point.y, box.max_point.y):
            for cz in _range(box.min_point.z, box.max_point.z):
                yield (cx, cy, cz)


class _SpatialGrid:
    """Maps grid cells → set of instance_ids occupying that cell."""

    def __init__(self) -> None:
        self._cells: Dict[_CellKey, Set[str]] = {}
        self._instance_cells: Dict[str, List[_CellKey]] = {}

    def insert(self, instance_id: str, box: BoundingBox) -> None:
        keys = list(_cell_keys_for_box(box))
        self._instance_cells[instance_id] = keys
        for key in keys:
            self._cells.setdefault(key, set()).add(instance_id)

    def remove(self, instance_id: str) -> None:
        for key in self._instance_cells.pop(instance_id, []):
            cell = self._cells.get(key)
            if cell:
                cell.discard(instance_id)
                if not cell:
                    del self._cells[key]

    def candidates(self, box: BoundingBox) -> Set[str]:
        """Return all instance_ids sharing at least one cell with *box*."""
        result: Set[str] = set()
        for key in _cell_keys_for_box(box):
            result.update(self._cells.get(key, set()))
        return result

    def update(self, instance_id: str, box: BoundingBox) -> None:
        self.remove(instance_id)
        self.insert(instance_id, box)

    def clear(self) -> None:
        self._cells.clear()
        self._instance_cells.clear()


# ---------------------------------------------------------------------------
# CollisionDetector
# ---------------------------------------------------------------------------

class CollisionDetector:
    """
    Maintains a registry of placed parts and detects AABB collisions.

    Usage
    -----
    detector = CollisionDetector()
    detector.register("part_a", metadata_a, pose_a)
    detector.register("part_b", metadata_b, pose_b)
    collisions = detector.check_all()

    # Before committing a new placement:
    candidates = detector.check_against_all("candidate", metadata, pose)
    if not candidates:
        detector.register("candidate", metadata, pose)
    """

    def __init__(self, broad_phase_margin: float = POSITION_TOLERANCE_LDU) -> None:
        """
        Parameters
        ----------
        broad_phase_margin:
            Extra margin added to each box during broad-phase candidate
            selection.  A small positive value catches near-touching parts.
        """
        self._parts: Dict[str, PlacedPart] = {}
        self._grid = _SpatialGrid()
        self._broad_margin = broad_phase_margin
        # Cache: frozenset pair → bool (True = colliding)
        self._cache: Dict[FrozenSet[str], bool] = {}

    # --- registration ---

    def register(self, instance_id: str, part: PartMetadata, pose: Pose) -> None:
        """Add or replace a part in the detector."""
        placed = PlacedPart(instance_id=instance_id, part=part, pose=pose)
        self._parts[instance_id] = placed
        self._grid.update(instance_id, placed.world_box())
        self._invalidate_cache_for(instance_id)

    def unregister(self, instance_id: str) -> None:
        """Remove a part from the detector."""
        if instance_id in self._parts:
            del self._parts[instance_id]
            self._grid.remove(instance_id)
            self._invalidate_cache_for(instance_id)

    def update_pose(self, instance_id: str, pose: Pose) -> None:
        """Update the pose of an already-registered part."""
        placed = self._parts[instance_id]
        placed.pose = pose
        placed.invalidate_cache()
        self._grid.update(instance_id, placed.world_box())
        self._invalidate_cache_for(instance_id)

    def clear(self) -> None:
        self._parts.clear()
        self._grid.clear()
        self._cache.clear()

    # --- queries ---

    def check_pair(self, id_a: str, id_b: str) -> Optional[CollisionResult]:
        """
        Test two registered parts for collision.

        Returns a CollisionResult if they overlap, else None.
        Uses the narrow-phase cache.
        """
        if id_a == id_b:
            return None
        key: FrozenSet[str] = frozenset({id_a, id_b})

        if key in self._cache:
            if not self._cache[key]:
                return None
            # Still need to build result — fall through.

        box_a = self._parts[id_a].world_box()
        box_b = self._parts[id_b].world_box()
        collides = box_a.intersects(box_b)
        self._cache[key] = collides

        if not collides:
            return None
        return CollisionResult(id_a=id_a, id_b=id_b, box_a=box_a, box_b=box_b)

    def check_against_all(
        self, instance_id: str, part: PartMetadata, pose: Pose
    ) -> List[CollisionResult]:
        """
        Check a *candidate* part (not yet registered) against all registered
        parts.  Returns a list of collisions (empty = safe to place).
        """
        candidate_box = world_box(part, pose)
        broad_box = expanded_box(candidate_box, self._broad_margin)
        candidate_ids = self._grid.candidates(broad_box) - {instance_id}

        results: List[CollisionResult] = []
        for other_id in candidate_ids:
            other_box = self._parts[other_id].world_box()
            if candidate_box.intersects(other_box):
                results.append(
                    CollisionResult(
                        id_a=instance_id,
                        id_b=other_id,
                        box_a=candidate_box,
                        box_b=other_box,
                    )
                )
        return results

    def check_all(self) -> List[CollisionResult]:
        """
        Run a full broad+narrow collision check across all registered parts.

        Returns every colliding pair (each pair reported once).
        """
        results: List[CollisionResult] = []
        seen: Set[FrozenSet[str]] = set()

        for instance_id, placed in self._parts.items():
            box = placed.world_box()
            broad_box = expanded_box(box, self._broad_margin)
            candidates = self._grid.candidates(broad_box) - {instance_id}

            for other_id in candidates:
                key: FrozenSet[str] = frozenset({instance_id, other_id})
                if key in seen:
                    continue
                seen.add(key)
                result = self.check_pair(instance_id, other_id)
                if result:
                    results.append(result)

        return results

    def has_any_collision(self) -> bool:
        """Return True as soon as the first collision is found."""
        seen: Set[FrozenSet[str]] = set()
        for instance_id, placed in self._parts.items():
            broad_box = expanded_box(placed.world_box(), self._broad_margin)
            for other_id in self._grid.candidates(broad_box) - {instance_id}:
                key: FrozenSet[str] = frozenset({instance_id, other_id})
                if key in seen:
                    continue
                seen.add(key)
                if self.check_pair(instance_id, other_id):
                    return True
        return False

    def registered_ids(self) -> List[str]:
        return list(self._parts.keys())

    def __len__(self) -> int:
        return len(self._parts)

    # --- cache helpers ---

    def _invalidate_cache_for(self, instance_id: str) -> None:
        stale = [k for k in self._cache if instance_id in k]
        for k in stale:
            del self._cache[k]
