"""
Part metadata definitions for the LEGO geometry engine.

Dimensions are stored in LDU (LEGO Drawing Units).
Stud counts (length × width) and height category are kept alongside the raw
LDU values so callers can work at whichever level of abstraction they prefer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple
from pathlib import Path

from ..core.constants import (
    STUD_SPACING_LDU,
    PLATE_HEIGHT_LDU,
    BRICK_HEIGHT_LDU,
)
from ..core.geometry import BoundingBox, Point3D


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class PartCategory(Enum):
    BRICK = auto()      # full-height brick (3 plates tall)
    PLATE = auto()      # 1-plate-tall flat part
    TILE = auto()       # plate with no studs on top
    SLOPE = auto()      # angled surface
    TECHNIC = auto()    # Technic beam / brick with axle holes
    OTHER = auto()


# ---------------------------------------------------------------------------
# SlopeGeometry  (Phase B)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SlopeGeometry:
    """
    Additional geometry descriptor for SLOPE category parts.

    The slope body is a trapezoidal prism that rises along the Z axis:
      - At z = 0 (front / low end): height = height_low_ldu
      - At z = depth (back / high end): height = height_high_ldu

    height_high_ldu must equal the part's PartDimensions.height_ldu so that
    the AABB (used for broad-phase collision) is still correct.

    flat_rows_at_high_end controls how many stud *rows* (counting from the
    high / back end) sit on a flat horizontal surface and therefore carry
    regular upward-facing studs.  Set to 0 for a fully tapered slope.
    """
    height_low_ldu: float
    height_high_ldu: float
    flat_rows_at_high_end: int = 1

    @property
    def delta_height_ldu(self) -> float:
        return self.height_high_ldu - self.height_low_ldu


# ---------------------------------------------------------------------------
# TechnicGeometry  (Phase B)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TechnicGeometry:
    """
    Additional geometry descriptor for TECHNIC category parts.

    hole_positions: stud-grid (col, row) coordinates of each axle hole.
    hole_axis:      'x' — holes run parallel to the X axis (default for
                    beams oriented along Z); 'z' — holes run along Z.
    """
    hole_positions: Tuple[Tuple[int, int], ...]
    hole_axis: str = "x"   # 'x' or 'z'


# ---------------------------------------------------------------------------
# HeightUnit
# ---------------------------------------------------------------------------

class HeightUnit(Enum):
    """Canonical vertical unit used to specify a part's height."""
    PLATE = auto()
    BRICK = auto()
    LDU = auto()


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PartDimensions:
    """
    Physical size of a part in LDU.

    *studs_x* and *studs_z* are the stud footprint (may be fractional for
    half-stud-offset parts, but are integers for all Phase A parts).
    *height_ldu* is the full height including the stud protrusion only where
    relevant for collision; bounding boxes are built from this value.
    """
    studs_x: int                # footprint along X (length)
    studs_z: int                # footprint along Z (width)
    height_ldu: float           # total height in LDU

    @property
    def width_ldu(self) -> float:
        return self.studs_x * STUD_SPACING_LDU

    @property
    def depth_ldu(self) -> float:
        return self.studs_z * STUD_SPACING_LDU

    def bounding_box(self) -> BoundingBox:
        """
        Return the local-space AABB for a part with this footprint.

        Origin is at the bottom-centre of the part's stud grid:
          X in [0, width],  Y in [0, height],  Z in [0, depth]
        """
        return BoundingBox(
            Point3D(0.0, 0.0, 0.0),
            Point3D(self.width_ldu, self.height_ldu, self.depth_ldu),
        )

    def __repr__(self) -> str:
        return (
            f"PartDimensions({self.studs_x}×{self.studs_z}, "
            f"h={self.height_ldu:.1f} LDU)"
        )


# ---------------------------------------------------------------------------
# PartMetadata
# ---------------------------------------------------------------------------

@dataclass
class PartMetadata:
    """
    Complete metadata record for a single LEGO part.

    Attributes
    ----------
    part_id:
        Unique string identifier (mirrors LDraw part numbers where possible,
        e.g. "3001" for the classic 2×4 brick).
    name:
        Human-readable name.
    category:
        High-level part family.
    dimensions:
        Physical size.
    mesh_path:
        Optional path to a 3-D mesh file (populated in Phase B+).
    ldraw_id:
        Original LDraw number if different from *part_id*.
    """
    part_id: str
    name: str
    category: PartCategory
    dimensions: PartDimensions
    mesh_path: Optional[str] = None
    ldraw_id: Optional[str] = None
    slope_geometry: Optional[SlopeGeometry] = None      # Phase B: set for SLOPE parts
    technic_geometry: Optional[TechnicGeometry] = None  # Phase B: set for TECHNIC parts

    # --- derived helpers ---

    @property
    def footprint(self) -> tuple[int, int]:
        """Return (studs_x, studs_z) footprint tuple."""
        return (self.dimensions.studs_x, self.dimensions.studs_z)

    def bounding_box(self) -> BoundingBox:
        return self.dimensions.bounding_box()

    # --- serialisation ---

    def to_dict(self) -> dict:
        d: dict = {
            "part_id": self.part_id,
            "name": self.name,
            "category": self.category.name,
            "studs_x": self.dimensions.studs_x,
            "studs_z": self.dimensions.studs_z,
            "height_ldu": self.dimensions.height_ldu,
            "mesh_path": self.mesh_path,
            "ldraw_id": self.ldraw_id,
        }
        if self.slope_geometry is not None:
            sg = self.slope_geometry
            d["slope_geometry"] = {
                "height_low_ldu": sg.height_low_ldu,
                "height_high_ldu": sg.height_high_ldu,
                "flat_rows_at_high_end": sg.flat_rows_at_high_end,
            }
        if self.technic_geometry is not None:
            tg = self.technic_geometry
            d["technic_geometry"] = {
                "hole_positions": list(tg.hole_positions),
                "hole_axis": tg.hole_axis,
            }
        return d

    @staticmethod
    def from_dict(data: dict) -> PartMetadata:
        slope_geometry: Optional[SlopeGeometry] = None
        if "slope_geometry" in data:
            sg = data["slope_geometry"]
            slope_geometry = SlopeGeometry(
                height_low_ldu=sg["height_low_ldu"],
                height_high_ldu=sg["height_high_ldu"],
                flat_rows_at_high_end=sg.get("flat_rows_at_high_end", 1),
            )
        technic_geometry: Optional[TechnicGeometry] = None
        if "technic_geometry" in data:
            tg = data["technic_geometry"]
            technic_geometry = TechnicGeometry(
                hole_positions=tuple(tuple(p) for p in tg["hole_positions"]),
                hole_axis=tg.get("hole_axis", "x"),
            )
        return PartMetadata(
            part_id=data["part_id"],
            name=data["name"],
            category=PartCategory[data["category"]],
            dimensions=PartDimensions(
                studs_x=data["studs_x"],
                studs_z=data["studs_z"],
                height_ldu=data["height_ldu"],
            ),
            mesh_path=data.get("mesh_path"),
            ldraw_id=data.get("ldraw_id"),
            slope_geometry=slope_geometry,
            technic_geometry=technic_geometry,
        )

    @staticmethod
    def from_json(path: str | Path) -> PartMetadata:
        with open(path) as f:
            return PartMetadata.from_dict(json.load(f))

    def to_json(self, path: str | Path) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def __repr__(self) -> str:
        return (
            f"PartMetadata(id={self.part_id!r}, name={self.name!r}, "
            f"category={self.category.name}, dims={self.dimensions!r})"
        )


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_brick(
    part_id: str,
    name: str,
    studs_x: int,
    studs_z: int,
    ldraw_id: Optional[str] = None,
) -> PartMetadata:
    """Create a standard full-height brick part (3 plates = 24 LDU tall)."""
    return PartMetadata(
        part_id=part_id,
        name=name,
        category=PartCategory.BRICK,
        dimensions=PartDimensions(
            studs_x=studs_x,
            studs_z=studs_z,
            height_ldu=float(BRICK_HEIGHT_LDU),
        ),
        ldraw_id=ldraw_id,
    )


def make_plate(
    part_id: str,
    name: str,
    studs_x: int,
    studs_z: int,
    ldraw_id: Optional[str] = None,
) -> PartMetadata:
    """Create a standard 1-plate-tall part (8 LDU tall)."""
    return PartMetadata(
        part_id=part_id,
        name=name,
        category=PartCategory.PLATE,
        dimensions=PartDimensions(
            studs_x=studs_x,
            studs_z=studs_z,
            height_ldu=float(PLATE_HEIGHT_LDU),
        ),
        ldraw_id=ldraw_id,
    )


def make_slope(
    part_id: str,
    name: str,
    studs_x: int,
    studs_z: int,
    height_low_ldu: float,
    height_high_ldu: float,
    flat_rows_at_high_end: int = 1,
    ldraw_id: Optional[str] = None,
) -> PartMetadata:
    """
    Create a slope part.

    The slope body rises from *height_low_ldu* at its front (z=0 in local
    space) to *height_high_ldu* at its back (z = studs_z × STUD_SPACING).
    The AABB height is set to *height_high_ldu* (the tallest extent).

    *flat_rows_at_high_end* controls how many stud rows at the high end
    carry normal upward-facing studs (default 1).  Set to 0 for a fully
    tapered wedge with no top studs.
    """
    return PartMetadata(
        part_id=part_id,
        name=name,
        category=PartCategory.SLOPE,
        dimensions=PartDimensions(
            studs_x=studs_x,
            studs_z=studs_z,
            height_ldu=float(height_high_ldu),
        ),
        slope_geometry=SlopeGeometry(
            height_low_ldu=float(height_low_ldu),
            height_high_ldu=float(height_high_ldu),
            flat_rows_at_high_end=flat_rows_at_high_end,
        ),
        ldraw_id=ldraw_id,
    )


def make_technic_brick(
    part_id: str,
    name: str,
    studs_x: int,
    studs_z: int,
    hole_positions: Optional[List[Tuple[int, int]]] = None,
    hole_axis: str = "x",
    ldraw_id: Optional[str] = None,
) -> PartMetadata:
    """
    Create a Technic brick (full-height, 24 LDU) with axle holes.

    *hole_positions* is a list of (col, row) stud-grid coordinates where
    axle holes are present.  When None, holes are placed at every stud
    position (i.e., a fully perforated beam).

    *hole_axis* is the axis the holes run along: 'x' (default, holes accept
    pins/axles from ±X) or 'z'.
    """
    if hole_positions is None:
        hole_positions = [
            (col, row)
            for col in range(studs_x)
            for row in range(studs_z)
        ]
    return PartMetadata(
        part_id=part_id,
        name=name,
        category=PartCategory.TECHNIC,
        dimensions=PartDimensions(
            studs_x=studs_x,
            studs_z=studs_z,
            height_ldu=float(BRICK_HEIGHT_LDU),
        ),
        technic_geometry=TechnicGeometry(
            hole_positions=tuple((c, r) for c, r in hole_positions),
            hole_axis=hole_axis,
        ),
        ldraw_id=ldraw_id,
    )
