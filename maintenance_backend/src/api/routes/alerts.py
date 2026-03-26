from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.api.schemas import AlertAcknowledgeRequest, AlertOut, AlertResolveRequest
from src.auth.security import get_current_user, require_roles
from src.db.models import Alert, AlertStatus, User
from src.db.session import get_db

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get(
    "",
    response_model=list[AlertOut],
    summary="List alerts",
    description="List alerts with optional filters.",
    operation_id="alerts_list",
)
def list_alerts(
    equipment_id: int | None = Query(None, description="Filter by equipment id"),
    status_filter: str | None = Query(None, description="Filter by status (OPEN, ACKNOWLEDGED, RESOLVED, SUPPRESSED)"),
    severity: str | None = Query(None, description="Filter by severity (INFO, WARN, CRITICAL)"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AlertOut]:
    """List alerts."""
    stmt = select(Alert)
    if equipment_id is not None:
        stmt = stmt.where(Alert.equipment_id == equipment_id)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    if severity:
        stmt = stmt.where(Alert.severity == severity)

    items = db.execute(stmt.order_by(desc(Alert.alert_ts)).limit(limit)).scalars().all()
    return [
        AlertOut(
            id=a.id,
            equipment_id=a.equipment_id,
            parameter_id=a.parameter_id,
            reading_id=a.reading_id,
            alert_ts=a.alert_ts,
            severity=a.severity.value,
            status=a.status.value,
            title=a.title,
            message=a.message,
            rule_type=a.rule_type.value,
            acknowledged_by=a.acknowledged_by,
            acknowledged_at=a.acknowledged_at,
            resolved_by=a.resolved_by,
            resolved_at=a.resolved_at,
            created_at=a.created_at,
        )
        for a in items
    ]


@router.post(
    "/{alert_id}/acknowledge",
    response_model=AlertOut,
    summary="Acknowledge alert",
    description="Acknowledge an OPEN alert.",
    operation_id="alerts_acknowledge",
)
def acknowledge_alert(
    alert_id: int,
    _: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "ENGINEER", "OPERATOR")),
) -> AlertOut:
    """Acknowledge alert."""
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if a.status != AlertStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only OPEN alerts can be acknowledged")

    a.status = AlertStatus.ACKNOWLEDGED
    a.acknowledged_by = user.id
    a.acknowledged_at = datetime.now(timezone.utc)
    db.add(a)
    db.commit()
    db.refresh(a)
    return AlertOut(
        id=a.id,
        equipment_id=a.equipment_id,
        parameter_id=a.parameter_id,
        reading_id=a.reading_id,
        alert_ts=a.alert_ts,
        severity=a.severity.value,
        status=a.status.value,
        title=a.title,
        message=a.message,
        rule_type=a.rule_type.value,
        acknowledged_by=a.acknowledged_by,
        acknowledged_at=a.acknowledged_at,
        resolved_by=a.resolved_by,
        resolved_at=a.resolved_at,
        created_at=a.created_at,
    )


@router.post(
    "/{alert_id}/resolve",
    response_model=AlertOut,
    summary="Resolve alert",
    description="Resolve an alert (ACKNOWLEDGED or OPEN).",
    operation_id="alerts_resolve",
)
def resolve_alert(
    alert_id: int,
    _: AlertResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> AlertOut:
    """Resolve alert."""
    a = db.get(Alert, alert_id)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if a.status not in (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only OPEN/ACKNOWLEDGED alerts can be resolved")

    a.status = AlertStatus.RESOLVED
    a.resolved_by = user.id
    a.resolved_at = datetime.now(timezone.utc)
    db.add(a)
    db.commit()
    db.refresh(a)
    return AlertOut(
        id=a.id,
        equipment_id=a.equipment_id,
        parameter_id=a.parameter_id,
        reading_id=a.reading_id,
        alert_ts=a.alert_ts,
        severity=a.severity.value,
        status=a.status.value,
        title=a.title,
        message=a.message,
        rule_type=a.rule_type.value,
        acknowledged_by=a.acknowledged_by,
        acknowledged_at=a.acknowledged_at,
        resolved_by=a.resolved_by,
        resolved_at=a.resolved_at,
        created_at=a.created_at,
    )
