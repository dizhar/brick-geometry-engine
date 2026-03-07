"""
Read-only routes for the part catalog.

Parts are loaded from the in-memory catalog (common_parts.py + slope_parts.py
+ technic_parts.py) and are not persisted to the database.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from brick_geometry.parts.part_catalog import PartCatalog
from brick_geometry.parts.common_parts import ALL_PARTS
from ..schemas import PartDimensionsResponse, PartListResponse, PartResponse

router = APIRouter(prefix="/parts", tags=["parts"])

# Build the catalog once at import time.
# ALL_PARTS is a dict; register_many expects a list.
_catalog = PartCatalog(name="default")
_catalog.register_many(list(ALL_PARTS.values()))

# Attempt to load slope and technic parts if they exist.
try:
    from brick_geometry.parts.slope_parts import ALL_SLOPES
    _catalog.register_many(list(ALL_SLOPES.values()), overwrite=True)
except ImportError:
    pass

try:
    from brick_geometry.parts.technic_parts import ALL_TECHNIC
    _catalog.register_many(list(ALL_TECHNIC.values()), overwrite=True)
except ImportError:
    pass


def _part_to_schema(part) -> PartResponse:
    dims = part.dimensions
    return PartResponse(
        part_id=part.part_id,
        category=part.category.name,
        dimensions=PartDimensionsResponse(
            studs_x=dims.studs_x,
            studs_z=dims.studs_z,
            height_ldu=dims.height_ldu,
            width_ldu=dims.width_ldu,
            depth_ldu=dims.depth_ldu,
        ),
        description=getattr(part, "name", None),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=PartListResponse)
def list_parts(
    category: Optional[str] = Query(None, description="Filter by category (e.g. BRICK, PLATE, SLOPE)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Return parts from the in-memory catalog, optionally filtered by category."""
    all_parts = list(_catalog)

    if category:
        cat_upper = category.upper()
        all_parts = [p for p in all_parts if p.category.name == cat_upper]

    total = len(all_parts)
    page = all_parts[skip : skip + limit]
    return PartListResponse(total=total, items=[_part_to_schema(p) for p in page])


@router.get("/{part_id}", response_model=PartResponse)
def get_part(part_id: str):
    """Fetch a single part by ID."""
    try:
        part = _catalog.get(part_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Part '{part_id}' not found")
    return _part_to_schema(part)
