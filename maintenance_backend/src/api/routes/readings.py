from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.api.schemas import ReadingCreate, ReadingOut
from src.auth.security import get_current_user, require_roles
from src.db.models import Reading, User
from src.db.session import get_db
from src.domain.alerts import evaluate_reading_and_maybe_create_alert

router = APIRouter(prefix="/readings", tags=["Readings"])


@router.post(
    "",
    response_model=ReadingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a reading",
    description="Insert a sensor/manual reading. Engineers/operators can ingest. Alerts may be generated automatically.",
    operation_id="readings_create",
)
def create_reading(
    payload: ReadingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "ENGINEER", "OPERATOR")),
) -> ReadingOut:
    """Create a reading and auto-generate alerts if needed."""
    r = Reading(
        equipment_id=payload.equipment_id,
        parameter_id=payload.parameter_id,
        reading_ts=payload.reading_ts,
        value_num=payload.value_num,
        value_text=payload.value_text,
        source=payload.source,
        quality=payload.quality,
        recorded_by=user.id if payload.source != "SENSOR" else None,
    )
    db.add(r)
    db.flush()  # assign id before alert generation

    evaluate_reading_and_maybe_create_alert(db, r)
    db.commit()
    db.refresh(r)

    return ReadingOut(
        id=r.id,
        equipment_id=r.equipment_id,
        parameter_id=r.parameter_id,
        reading_ts=r.reading_ts,
        value_num=r.value_num,
        value_text=r.value_text,
        source=r.source.value,
        quality=r.quality.value,
        recorded_by=r.recorded_by,
        created_at=r.created_at,
    )


@router.get(
    "",
    response_model=list[ReadingOut],
    summary="List readings",
    description="List readings with optional filters (equipment_id, parameter_id).",
    operation_id="readings_list",
)
def list_readings(
    equipment_id: int | None = Query(None, description="Filter by equipment id"),
    parameter_id: int | None = Query(None, description="Filter by parameter id"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ReadingOut]:
    """List readings."""
    stmt = select(Reading)
    if equipment_id is not None:
        stmt = stmt.where(Reading.equipment_id == equipment_id)
    if parameter_id is not None:
        stmt = stmt.where(Reading.parameter_id == parameter_id)

    items = db.execute(stmt.order_by(desc(Reading.reading_ts)).limit(limit)).scalars().all()
    return [
        ReadingOut(
            id=r.id,
            equipment_id=r.equipment_id,
            parameter_id=r.parameter_id,
            reading_ts=r.reading_ts,
            value_num=r.value_num,
            value_text=r.value_text,
            source=r.source.value,
            quality=r.quality.value,
            recorded_by=r.recorded_by,
            created_at=r.created_at,
        )
        for r in items
    ]
