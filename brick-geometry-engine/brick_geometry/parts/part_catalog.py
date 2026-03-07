"""
PartCatalog — a registry of PartMetadata records with load/save and query support.

The catalog can be populated programmatically (e.g. from common_parts.py) or
loaded from a JSON file that contains an array of serialised PartMetadata dicts.

JSON schema (per entry):
{
  "part_id":    "brick_2x4",
  "name":       "Brick 2×4",
  "category":   "BRICK",
  "studs_x":    2,
  "studs_z":    4,
  "height_ldu": 24.0,
  "mesh_path":  null,
  "ldraw_id":   "3001"
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional

from .part_metadata import PartCategory, PartMetadata
from .common_parts import ALL_PARTS
from ..utils.validation import validate_part_id


class PartCatalog:
    """
    Central registry for PartMetadata.

    Supports:
    - Programmatic registration
    - Bulk load/save via JSON
    - Queries by ID, category, footprint, LDraw number, and arbitrary predicate
    """

    def __init__(self, name: str = "catalog") -> None:
        self.name = name
        self._parts: Dict[str, PartMetadata] = {}

    # -----------------------------------------------------------------------
    # Registration
    # -----------------------------------------------------------------------

    def register(self, part: PartMetadata, overwrite: bool = False) -> None:
        """Add *part* to the catalog."""
        if part.part_id in self._parts and not overwrite:
            raise ValueError(
                f"Part {part.part_id!r} is already registered. "
                "Pass overwrite=True to replace it."
            )
        self._parts[part.part_id] = part

    def register_many(
        self, parts: List[PartMetadata], overwrite: bool = False
    ) -> None:
        for part in parts:
            self.register(part, overwrite=overwrite)

    def unregister(self, part_id: str) -> PartMetadata:
        pid = validate_part_id(part_id)
        try:
            return self._parts.pop(pid)
        except KeyError:
            raise KeyError(f"Part {pid!r} is not in the catalog.")

    # -----------------------------------------------------------------------
    # Lookup
    # -----------------------------------------------------------------------

    def get(self, part_id: str) -> PartMetadata:
        pid = validate_part_id(part_id)
        try:
            return self._parts[pid]
        except KeyError:
            raise KeyError(
                f"Part {pid!r} not found. "
                f"Catalog contains {len(self._parts)} part(s)."
            )

    def get_or_none(self, part_id: str) -> Optional[PartMetadata]:
        return self._parts.get(part_id)

    def __contains__(self, part_id: str) -> bool:
        return part_id in self._parts

    def __len__(self) -> int:
        return len(self._parts)

    def __iter__(self) -> Iterator[PartMetadata]:
        return iter(self._parts.values())

    # -----------------------------------------------------------------------
    # Queries
    # -----------------------------------------------------------------------

    def by_category(self, category: PartCategory) -> List[PartMetadata]:
        return [p for p in self._parts.values() if p.category == category]

    def by_footprint(self, studs_x: int, studs_z: int) -> List[PartMetadata]:
        """Return all parts with the given stud footprint (order-insensitive)."""
        return [
            p for p in self._parts.values()
            if (p.dimensions.studs_x == studs_x and p.dimensions.studs_z == studs_z)
            or (p.dimensions.studs_x == studs_z and p.dimensions.studs_z == studs_x)
        ]

    def by_ldraw_id(self, ldraw_id: str) -> Optional[PartMetadata]:
        for p in self._parts.values():
            if p.ldraw_id == ldraw_id:
                return p
        return None

    def where(self, predicate: Callable[[PartMetadata], bool]) -> List[PartMetadata]:
        """Return all parts for which *predicate* returns True."""
        return [p for p in self._parts.values() if predicate(p)]

    def all(self) -> List[PartMetadata]:
        return list(self._parts.values())

    def part_ids(self) -> List[str]:
        return sorted(self._parts.keys())

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def save_json(self, path: str | Path) -> None:
        """Serialise the entire catalog to a JSON file."""
        data = [p.to_dict() for p in self._parts.values()]
        with open(path, "w") as f:
            json.dump({"name": self.name, "parts": data}, f, indent=2)

    @staticmethod
    def load_json(path: str | Path) -> "PartCatalog":
        """Load a catalog from a JSON file created by :meth:`save_json`."""
        with open(path) as f:
            raw = json.load(f)
        catalog = PartCatalog(name=raw.get("name", "catalog"))
        for entry in raw.get("parts", []):
            catalog.register(PartMetadata.from_dict(entry))
        return catalog

    def merge(self, other: "PartCatalog", overwrite: bool = False) -> None:
        """Copy all parts from *other* into this catalog."""
        for part in other:
            self.register(part, overwrite=overwrite)

    # -----------------------------------------------------------------------
    # Factory
    # -----------------------------------------------------------------------

    @staticmethod
    def default() -> "PartCatalog":
        """Return a catalog pre-loaded with all Phase-A common parts."""
        catalog = PartCatalog(name="phase_a_default")
        catalog.register_many(list(ALL_PARTS.values()))
        return catalog

    # -----------------------------------------------------------------------
    # Misc
    # -----------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"PartCatalog({self.name!r}, {len(self._parts)} parts)"
