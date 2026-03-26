from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.schemas import EquipmentCreate, EquipmentOut, EquipmentUpdate
from src.auth.security import get_current_user, require_roles
from src.db.models import Equipment, User
from src.db.session import get_db

router = APIRouter(prefix="/equipment", tags=["Equipment"])


@router.get(
    "",
    response_model=list[EquipmentOut],
    summary="List equipment",
    description="List equipment records. Requires authentication.",
    operation_id="equipment_list",
)
def list_equipment(
    q: str | None = Query(None, description="Optional search by asset_tag or name"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[EquipmentOut]:
    """List equipment with optional search."""
    stmt = select(Equipment)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Equipment.asset_tag.like(like)) | (Equipment.name.like(like)))
    items = db.execute(stmt.order_by(Equipment.id.desc())).scalars().all()
    return [
        EquipmentOut(
            id=e.id,
            asset_tag=e.asset_tag,
            name=e.name,
            equipment_type=e.equipment_type,
            manufacturer=e.manufacturer,
            model=e.model,
            serial_number=e.serial_number,
            location=e.location,
            status=e.status.value,
            installed_at=e.installed_at,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in items
    ]


@router.get(
    "/{equipment_id}",
    response_model=EquipmentOut,
    summary="Get equipment",
    description="Get one equipment record by id.",
    operation_id="equipment_get",
)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> EquipmentOut:
    """Get equipment by id."""
    e = db.get(Equipment, equipment_id)
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    return EquipmentOut(
        id=e.id,
        asset_tag=e.asset_tag,
        name=e.name,
        equipment_type=e.equipment_type,
        manufacturer=e.manufacturer,
        model=e.model,
        serial_number=e.serial_number,
        location=e.location,
        status=e.status.value,
        installed_at=e.installed_at,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


@router.post(
    "",
    response_model=EquipmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create equipment",
    description="Create a new equipment record (ADMIN/ENGINEER).",
    operation_id="equipment_create",
)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> EquipmentOut:
    """Create equipment."""
    existing = db.execute(select(Equipment).where(Equipment.asset_tag == payload.asset_tag)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="asset_tag already exists")

    e = Equipment(
        asset_tag=payload.asset_tag,
        name=payload.name,
        equipment_type=payload.equipment_type,
        manufacturer=payload.manufacturer,
        model=payload.model,
        serial_number=payload.serial_number,
        location=payload.location,
        status=payload.status,
        installed_at=payload.installed_at,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return get_equipment(e.id, db, _)


@router.put(
    "/{equipment_id}",
    response_model=EquipmentOut,
    summary="Update equipment",
    description="Update an equipment record (ADMIN/ENGINEER).",
    operation_id="equipment_update",
)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> EquipmentOut:
    """Update equipment."""
    e = db.get(Equipment, equipment_id)
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(e, k, v)

    db.add(e)
    db.commit()
    db.refresh(e)
    return EquipmentOut(
        id=e.id,
        asset_tag=e.asset_tag,
        name=e.name,
        equipment_type=e.equipment_type,
        manufacturer=e.manufacturer,
        model=e.model,
        serial_number=e.serial_number,
        location=e.location,
        status=e.status.value,
        installed_at=e.installed_at,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


@router.delete(
    "/{equipment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete equipment",
    description="Delete equipment (ADMIN only). Cascades readings/thresholds/work-orders via DB FK.",
    operation_id="equipment_delete",
)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN")),
) -> None:
    """Delete equipment."""
    e = db.get(Equipment, equipment_id)
    if not e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipment not found")
    db.delete(e)
    db.commit()
    return None
