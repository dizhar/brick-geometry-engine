"""
Pydantic request/response schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Assembly schemas
# ---------------------------------------------------------------------------

class AssemblyCreate(BaseModel):
    name: str
    # Optional pre-built assembly snapshot (output of Assembly.to_dict()).
    # Omit to start with an empty assembly.
    data: Optional[Dict[str, Any]] = None


class AssemblyUpdate(BaseModel):
    name: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class AssemblyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class AssemblyListResponse(BaseModel):
    total: int
    items: List[AssemblyResponse]


# ---------------------------------------------------------------------------
# Part schemas
# ---------------------------------------------------------------------------

class PartDimensionsResponse(BaseModel):
    studs_x: int
    studs_z: int
    height_ldu: float
    width_ldu: float
    depth_ldu: float


class PartResponse(BaseModel):
    part_id: str
    category: str
    dimensions: PartDimensionsResponse
    description: Optional[str] = None


class PartListResponse(BaseModel):
    total: int
    items: List[PartResponse]
