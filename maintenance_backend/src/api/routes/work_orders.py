from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from src.api.schemas import (
    WorkOrderCreate,
    WorkOrderOut,
    WorkOrderPartOut,
    WorkOrderPartUseRequest,
    WorkOrderTaskCreate,
    WorkOrderTaskOut,
    WorkOrderTaskUpdate,
    WorkOrderUpdate,
    WorkOrderOutcomeCreate,
    WorkOrderOutcomeOut,
)
from src.auth.security import get_current_user, require_roles
from src.db.models import (
    Part,
    User,
    WorkOrder,
    WorkOrderOutcome,
    WorkOrderPart,
    WorkOrderStatus,
    WorkOrderTask,
)
from src.db.session import get_db

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


@router.get(
    "",
    response_model=list[WorkOrderOut],
    summary="List work orders",
    description="List work orders with optional filters.",
    operation_id="work_orders_list",
)
def list_work_orders(
    equipment_id: int | None = Query(None, description="Filter by equipment id"),
    status_filter: str | None = Query(None, description="Filter by status"),
    assigned_to: int | None = Query(None, description="Filter by assignee user id"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[WorkOrderOut]:
    """List work orders."""
    stmt = select(WorkOrder)
    if equipment_id is not None:
        stmt = stmt.where(WorkOrder.equipment_id == equipment_id)
    if status_filter:
        stmt = stmt.where(WorkOrder.status == status_filter)
    if assigned_to is not None:
        stmt = stmt.where(WorkOrder.assigned_to == assigned_to)

    items = db.execute(stmt.order_by(desc(WorkOrder.updated_at)).limit(limit)).scalars().all()
    return [
        WorkOrderOut(
            id=wo.id,
            equipment_id=wo.equipment_id,
            alert_id=wo.alert_id,
            created_by=wo.created_by,
            assigned_to=wo.assigned_to,
            priority=wo.priority.value,
            status=wo.status.value,
            title=wo.title,
            description=wo.description,
            due_date=wo.due_date,
            started_at=wo.started_at,
            completed_at=wo.completed_at,
            created_at=wo.created_at,
            updated_at=wo.updated_at,
        )
        for wo in items
    ]


@router.get(
    "/{work_order_id}",
    response_model=WorkOrderOut,
    summary="Get work order",
    description="Get a work order by id.",
    operation_id="work_orders_get",
)
def get_work_order(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WorkOrderOut:
    """Get one work order."""
    wo = db.get(WorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    return WorkOrderOut(
        id=wo.id,
        equipment_id=wo.equipment_id,
        alert_id=wo.alert_id,
        created_by=wo.created_by,
        assigned_to=wo.assigned_to,
        priority=wo.priority.value,
        status=wo.status.value,
        title=wo.title,
        description=wo.description,
        due_date=wo.due_date,
        started_at=wo.started_at,
        completed_at=wo.completed_at,
        created_at=wo.created_at,
        updated_at=wo.updated_at,
    )


@router.post(
    "",
    response_model=WorkOrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create work order",
    description="Create a work order (ADMIN/ENGINEER).",
    operation_id="work_orders_create",
)
def create_work_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> WorkOrderOut:
    """Create a work order."""
    wo = WorkOrder(
        equipment_id=payload.equipment_id,
        alert_id=payload.alert_id,
        created_by=user.id,
        assigned_to=payload.assigned_to,
        priority=payload.priority,
        status=WorkOrderStatus.OPEN,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    db.add(wo)
    db.commit()
    db.refresh(wo)
    return get_work_order(wo.id, db, user)


@router.put(
    "/{work_order_id}",
    response_model=WorkOrderOut,
    summary="Update work order",
    description="Update work order fields/status (ADMIN/ENGINEER).",
    operation_id="work_orders_update",
)
def update_work_order(
    work_order_id: int,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> WorkOrderOut:
    """Update work order."""
    wo = db.get(WorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    update_data = payload.model_dump(exclude_unset=True)
    new_status = update_data.get("status")
    if new_status:
        # Set timestamps for lifecycle transitions
        if new_status == "IN_PROGRESS" and wo.started_at is None:
            wo.started_at = datetime.now(timezone.utc)
        if new_status in ("COMPLETED", "CANCELLED"):
            wo.completed_at = datetime.now(timezone.utc)

    for k, v in update_data.items():
        setattr(wo, k, v)

    db.add(wo)
    db.commit()
    db.refresh(wo)
    return WorkOrderOut(
        id=wo.id,
        equipment_id=wo.equipment_id,
        alert_id=wo.alert_id,
        created_by=wo.created_by,
        assigned_to=wo.assigned_to,
        priority=wo.priority.value,
        status=wo.status.value,
        title=wo.title,
        description=wo.description,
        due_date=wo.due_date,
        started_at=wo.started_at,
        completed_at=wo.completed_at,
        created_at=wo.created_at,
        updated_at=wo.updated_at,
    )


tasks_router = APIRouter(prefix="/work-orders/{work_order_id}/tasks", tags=["Work Order Tasks"])
parts_router = APIRouter(prefix="/work-orders/{work_order_id}/parts", tags=["Work Order Parts"])
outcome_router = APIRouter(prefix="/work-orders/{work_order_id}/outcome", tags=["Work Order Outcomes"])


@tasks_router.get(
    "",
    response_model=list[WorkOrderTaskOut],
    summary="List work order tasks",
    description="List tasks for a work order.",
    operation_id="work_order_tasks_list",
)
def list_tasks(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[WorkOrderTaskOut]:
    """List tasks."""
    tasks = db.execute(
        select(WorkOrderTask).where(WorkOrderTask.work_order_id == work_order_id).order_by(WorkOrderTask.sort_order.asc())
    ).scalars().all()
    return [
        WorkOrderTaskOut(
            id=t.id,
            work_order_id=t.work_order_id,
            title=t.title,
            description=t.description,
            status=t.status.value,
            sort_order=t.sort_order,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]


@tasks_router.post(
    "",
    response_model=WorkOrderTaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create work order task",
    description="Add a task to a work order (ADMIN/ENGINEER).",
    operation_id="work_order_tasks_create",
)
def create_task(
    work_order_id: int,
    payload: WorkOrderTaskCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> WorkOrderTaskOut:
    """Create a task."""
    wo = db.get(WorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    t = WorkOrderTask(work_order_id=work_order_id, title=payload.title, description=payload.description, sort_order=payload.sort_order)
    db.add(t)
    db.commit()
    db.refresh(t)
    return WorkOrderTaskOut(
        id=t.id,
        work_order_id=t.work_order_id,
        title=t.title,
        description=t.description,
        status=t.status.value,
        sort_order=t.sort_order,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@tasks_router.put(
    "/{task_id}",
    response_model=WorkOrderTaskOut,
    summary="Update work order task",
    description="Update work order task (ADMIN/ENGINEER).",
    operation_id="work_order_tasks_update",
)
def update_task(
    work_order_id: int,
    task_id: int,
    payload: WorkOrderTaskUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> WorkOrderTaskOut:
    """Update a task."""
    t = db.get(WorkOrderTask, task_id)
    if not t or t.work_order_id != work_order_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.add(t)
    db.commit()
    db.refresh(t)
    return WorkOrderTaskOut(
        id=t.id,
        work_order_id=t.work_order_id,
        title=t.title,
        description=t.description,
        status=t.status.value,
        sort_order=t.sort_order,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@parts_router.get(
    "",
    response_model=list[WorkOrderPartOut],
    summary="List parts used on work order",
    description="List parts usage records for a work order.",
    operation_id="work_order_parts_list",
)
def list_parts_usage(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[WorkOrderPartOut]:
    """List parts used."""
    items = db.execute(select(WorkOrderPart).where(WorkOrderPart.work_order_id == work_order_id).order_by(desc(WorkOrderPart.used_at))).scalars().all()
    return [
        WorkOrderPartOut(
            id=wop.id,
            work_order_id=wop.work_order_id,
            part_id=wop.part_id,
            quantity_used=wop.quantity_used,
            unit_cost_at_use=wop.unit_cost_at_use,
            used_at=wop.used_at,
            used_by=wop.used_by,
        )
        for wop in items
    ]


@parts_router.post(
    "",
    response_model=WorkOrderPartOut,
    status_code=status.HTTP_201_CREATED,
    summary="Use part on work order",
    description="Record part usage and decrement inventory (ADMIN/ENGINEER).",
    operation_id="work_order_parts_use",
)
def use_part(
    work_order_id: int,
    payload: WorkOrderPartUseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> WorkOrderPartOut:
    """Use a part: create work_order_parts record and decrement parts.quantity_on_hand."""
    wo = db.get(WorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    part = db.get(Part, payload.part_id)
    if not part or not part.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")

    if part.quantity_on_hand < payload.quantity_used:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient inventory")

    wop = WorkOrderPart(
        work_order_id=work_order_id,
        part_id=payload.part_id,
        quantity_used=payload.quantity_used,
        unit_cost_at_use=part.unit_cost,
        used_by=user.id,
    )
    part.quantity_on_hand = part.quantity_on_hand - payload.quantity_used
    db.add_all([wop, part])
    db.commit()
    db.refresh(wop)
    return WorkOrderPartOut(
        id=wop.id,
        work_order_id=wop.work_order_id,
        part_id=wop.part_id,
        quantity_used=wop.quantity_used,
        unit_cost_at_use=wop.unit_cost_at_use,
        used_at=wop.used_at,
        used_by=wop.used_by,
    )


@outcome_router.get(
    "",
    response_model=WorkOrderOutcomeOut,
    summary="Get work order outcome",
    description="Get outcome record for a work order if present.",
    operation_id="work_order_outcome_get",
)
def get_outcome(
    work_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> WorkOrderOutcomeOut:
    """Get outcome."""
    outcome = db.execute(select(WorkOrderOutcome).where(WorkOrderOutcome.work_order_id == work_order_id)).scalar_one_or_none()
    if not outcome:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outcome not found")
    return WorkOrderOutcomeOut(
        id=outcome.id,
        work_order_id=outcome.work_order_id,
        outcome_code=outcome.outcome_code.value,
        root_cause=outcome.root_cause,
        corrective_action=outcome.corrective_action,
        notes=outcome.notes,
        downtime_minutes=outcome.downtime_minutes,
        cost_total=outcome.cost_total,
        recorded_by=outcome.recorded_by,
        recorded_at=outcome.recorded_at,
    )


@outcome_router.post(
    "",
    response_model=WorkOrderOutcomeOut,
    summary="Record work order outcome",
    description="Create/update outcome record. Sets cost_total from parts used (ADMIN/ENGINEER).",
    operation_id="work_order_outcome_record",
)
def record_outcome(
    work_order_id: int,
    payload: WorkOrderOutcomeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("ADMIN", "ENGINEER")),
) -> WorkOrderOutcomeOut:
    """Create or update work order outcome. Computes total parts cost."""
    wo = db.get(WorkOrder, work_order_id)
    if not wo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    parts_cost = db.execute(
        select(func.coalesce(func.sum(WorkOrderPart.quantity_used * WorkOrderPart.unit_cost_at_use), 0))
        .where(WorkOrderPart.work_order_id == work_order_id)
    ).scalar_one()
    cost_total = Decimal(str(parts_cost))

    existing = db.execute(select(WorkOrderOutcome).where(WorkOrderOutcome.work_order_id == work_order_id)).scalar_one_or_none()
    if existing:
        existing.outcome_code = payload.outcome_code
        existing.root_cause = payload.root_cause
        existing.corrective_action = payload.corrective_action
        existing.notes = payload.notes
        existing.downtime_minutes = payload.downtime_minutes
        existing.cost_total = cost_total
        existing.recorded_by = user.id
        db.add(existing)
        db.commit()
        db.refresh(existing)
        outcome = existing
    else:
        outcome = WorkOrderOutcome(
            work_order_id=work_order_id,
            outcome_code=payload.outcome_code,
            root_cause=payload.root_cause,
            corrective_action=payload.corrective_action,
            notes=payload.notes,
            downtime_minutes=payload.downtime_minutes,
            cost_total=cost_total,
            recorded_by=user.id,
        )
        db.add(outcome)
        db.commit()
        db.refresh(outcome)

    return WorkOrderOutcomeOut(
        id=outcome.id,
        work_order_id=outcome.work_order_id,
        outcome_code=outcome.outcome_code.value,
        root_cause=outcome.root_cause,
        corrective_action=outcome.corrective_action,
        notes=outcome.notes,
        downtime_minutes=outcome.downtime_minutes,
        cost_total=outcome.cost_total,
        recorded_by=outcome.recorded_by,
        recorded_at=outcome.recorded_at,
    )


# Re-export subrouters for inclusion in main app
subrouters = [tasks_router, parts_router, outcome_router]
