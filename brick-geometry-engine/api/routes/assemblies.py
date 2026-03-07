"""
CRUD routes for assemblies.

Assemblies are persisted as JSON snapshots (Assembly.to_dict() format) in
the PostgreSQL `assemblies` table.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AssemblyRecord
from ..schemas import (
    AssemblyCreate,
    AssemblyListResponse,
    AssemblyResponse,
    AssemblyUpdate,
)

router = APIRouter(prefix="/assemblies", tags=["assemblies"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_404(assembly_id: uuid.UUID, db: Session) -> AssemblyRecord:
    record = db.get(AssemblyRecord, assembly_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Assembly not found")
    return record


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=AssemblyListResponse)
def list_assemblies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return a paginated list of stored assemblies."""
    query = db.query(AssemblyRecord).order_by(AssemblyRecord.created_at.desc())
    total = query.count()
    records = query.offset(skip).limit(limit).all()
    return AssemblyListResponse(total=total, items=records)


@router.post("", response_model=AssemblyResponse, status_code=201)
def create_assembly(body: AssemblyCreate, db: Session = Depends(get_db)):
    """Create a new assembly record."""
    data = body.data if body.data is not None else {"name": body.name, "nodes": [], "bonds": []}
    record = AssemblyRecord(name=body.name, data=data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{assembly_id}", response_model=AssemblyResponse)
def get_assembly(assembly_id: uuid.UUID, db: Session = Depends(get_db)):
    """Fetch a single assembly by ID."""
    return _get_or_404(assembly_id, db)


@router.put("/{assembly_id}", response_model=AssemblyResponse)
def update_assembly(
    assembly_id: uuid.UUID,
    body: AssemblyUpdate,
    db: Session = Depends(get_db),
):
    """Replace the name and/or data of an existing assembly."""
    record = _get_or_404(assembly_id, db)
    if body.name is not None:
        record.name = body.name
    if body.data is not None:
        record.data = body.data
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{assembly_id}", status_code=204)
def delete_assembly(assembly_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete an assembly record."""
    record = _get_or_404(assembly_id, db)
    db.delete(record)
    db.commit()
