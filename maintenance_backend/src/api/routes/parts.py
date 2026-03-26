from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.schemas import PartCreate, PartOut, PartUpdate
from src.auth.security import get_current_user, require_roles
from src.db.models import Part, User
from src.db.session import get_db

router = APIRouter(prefix="/parts", tags=["Spare Parts"])


@router.get(
    "",
    response_model=list[PartOut],
    summary="List parts",
    description="List spare parts (inventory).",
    operation_id="parts_list",
)
def list_parts(
    q: str | None = Query(None, description="Search by SKU or name"),
    active_only: bool = Query(False, description="Only active parts"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PartOut]:
    """List parts."""
    stmt = select(Part)
    if active_only:
        stmt = stmt.where(Part.is_active.is_(True))
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Part.sku.like(like)) | (Part.name.like(like)))

    items = db.execute(stmt.order_by(Part.sku.asc())).scalars().all()
    return [
        PartOut(
            id=p.id,
            sku=p.sku,
            name=p.name,
            description=p.description,
            unit_cost=p.unit_cost,
            quantity_on_hand=p.quantity_on_hand,
            reorder_level=p.reorder_level,
            location=p.location,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in items
    ]


@router.post(
    "",
    response_model=PartOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create part",
    description="Create a spare part (ADMIN/ENGINEER).",
    operation_id="parts_create",
)
def create_part(
    payload: PartCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> PartOut:
    """Create part."""
    existing = db.execute(select(Part).where(Part.sku == payload.sku)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="SKU already exists")

    p = Part(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return PartOut(
        id=p.id,
        sku=p.sku,
        name=p.name,
        description=p.description,
        unit_cost=p.unit_cost,
        quantity_on_hand=p.quantity_on_hand,
        reorder_level=p.reorder_level,
        location=p.location,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.put(
    "/{part_id}",
    response_model=PartOut,
    summary="Update part",
    description="Update a spare part (ADMIN/ENGINEER).",
    operation_id="parts_update",
)
def update_part(
    part_id: int,
    payload: PartUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> PartOut:
    """Update part."""
    p = db.get(Part, part_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)

    db.add(p)
    db.commit()
    db.refresh(p)
    return PartOut(
        id=p.id,
        sku=p.sku,
        name=p.name,
        description=p.description,
        unit_cost=p.unit_cost,
        quantity_on_hand=p.quantity_on_hand,
        reorder_level=p.reorder_level,
        location=p.location,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
