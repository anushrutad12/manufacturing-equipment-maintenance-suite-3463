from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session

from src.api.schemas import (
    ParameterCreate,
    ParameterOut,
    ParameterUpdate,
    ThresholdCreate,
    ThresholdOut,
)
from src.auth.security import get_current_user, require_roles
from src.db.models import Parameter, ParameterThreshold, User
from src.db.session import get_db

router = APIRouter(prefix="/parameters", tags=["Parameters"])


@router.get(
    "",
    response_model=list[ParameterOut],
    summary="List parameters",
    description="List parameter definitions.",
    operation_id="parameters_list",
)
def list_parameters(
    active_only: bool = Query(False, description="If true, only return active parameters"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ParameterOut]:
    """List parameters."""
    stmt = select(Parameter)
    if active_only:
        stmt = stmt.where(Parameter.is_active.is_(True))
    items = db.execute(stmt.order_by(Parameter.code.asc())).scalars().all()
    return [
        ParameterOut(
            id=p.id,
            code=p.code,
            name=p.name,
            unit=p.unit,
            data_type=p.data_type.value,
            description=p.description,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in items
    ]


@router.post(
    "",
    response_model=ParameterOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create parameter",
    description="Create a new parameter definition (ADMIN/ENGINEER).",
    operation_id="parameters_create",
)
def create_parameter(
    payload: ParameterCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> ParameterOut:
    """Create parameter."""
    existing = db.execute(select(Parameter).where(Parameter.code == payload.code)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Parameter code already exists")
    p = Parameter(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return ParameterOut(
        id=p.id,
        code=p.code,
        name=p.name,
        unit=p.unit,
        data_type=p.data_type.value,
        description=p.description,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.put(
    "/{parameter_id}",
    response_model=ParameterOut,
    summary="Update parameter",
    description="Update parameter definition (ADMIN/ENGINEER).",
    operation_id="parameters_update",
)
def update_parameter(
    parameter_id: int,
    payload: ParameterUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> ParameterOut:
    """Update parameter."""
    p = db.get(Parameter, parameter_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parameter not found")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)

    db.add(p)
    db.commit()
    db.refresh(p)
    return ParameterOut(
        id=p.id,
        code=p.code,
        name=p.name,
        unit=p.unit,
        data_type=p.data_type.value,
        description=p.description,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


thresholds_router = APIRouter(prefix="/equipment/{equipment_id}/thresholds", tags=["Thresholds"])


@thresholds_router.get(
    "",
    response_model=list[ThresholdOut],
    summary="List thresholds",
    description="List thresholds for a given equipment.",
    operation_id="thresholds_list",
)
def list_thresholds(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ThresholdOut]:
    """List thresholds by equipment."""
    items = db.execute(
        select(ParameterThreshold).where(ParameterThreshold.equipment_id == equipment_id).order_by(desc(ParameterThreshold.id))
    ).scalars().all()
    return [
        ThresholdOut(
            id=t.id,
            equipment_id=t.equipment_id,
            parameter_id=t.parameter_id,
            warn_low=t.warn_low,
            warn_high=t.warn_high,
            crit_low=t.crit_low,
            crit_high=t.crit_high,
            baseline_mean=t.baseline_mean,
            baseline_stddev=t.baseline_stddev,
            window_size=t.window_size,
            is_active=t.is_active,
            effective_from=t.effective_from,
            effective_to=t.effective_to,
            created_by=t.created_by,
            created_at=t.created_at,
        )
        for t in items
    ]


@thresholds_router.post(
    "",
    response_model=ThresholdOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create threshold",
    description="Create a new threshold record for equipment+parameter (ADMIN/ENGINEER). Previous active thresholds are closed.",
    operation_id="thresholds_create",
)
def create_threshold(
    equipment_id: int,
    payload: ThresholdCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> ThresholdOut:
    """Create a new threshold set and deactivate previous active one for same equipment+parameter."""
    # Close any previous active threshold for equipment+parameter
    db.execute(
        update(ParameterThreshold)
        .where(
            ParameterThreshold.equipment_id == equipment_id,
            ParameterThreshold.parameter_id == payload.parameter_id,
            ParameterThreshold.is_active.is_(True),
            ParameterThreshold.effective_to.is_(None),
        )
        .values(is_active=False, effective_to=func.now())  # type: ignore[name-defined]
    )

    t = ParameterThreshold(
        equipment_id=equipment_id,
        parameter_id=payload.parameter_id,
        warn_low=payload.warn_low,
        warn_high=payload.warn_high,
        crit_low=payload.crit_low,
        crit_high=payload.crit_high,
        baseline_mean=payload.baseline_mean,
        baseline_stddev=payload.baseline_stddev,
        window_size=payload.window_size,
        is_active=payload.is_active,
        created_by=user.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return ThresholdOut(
        id=t.id,
        equipment_id=t.equipment_id,
        parameter_id=t.parameter_id,
        warn_low=t.warn_low,
        warn_high=t.warn_high,
        crit_low=t.crit_low,
        crit_high=t.crit_high,
        baseline_mean=t.baseline_mean,
        baseline_stddev=t.baseline_stddev,
        window_size=t.window_size,
        is_active=t.is_active,
        effective_from=t.effective_from,
        effective_to=t.effective_to,
        created_by=t.created_by,
        created_at=t.created_at,
    )
