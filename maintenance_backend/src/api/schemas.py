from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


# -----------------------
# Auth
# -----------------------
class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")


class UserPublic(BaseModel):
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email")
    full_name: str | None = Field(None, description="Full name")
    role: Literal["ADMIN", "ENGINEER", "OPERATOR"] = Field(..., description="Role")
    is_active: bool = Field(..., description="Whether user is active")


# -----------------------
# Equipment
# -----------------------
class EquipmentCreate(BaseModel):
    asset_tag: str = Field(..., description="Unique asset tag (e.g., CNC-001)")
    name: str = Field(..., description="Display name")
    equipment_type: str | None = Field(None, description="Equipment type/category")
    manufacturer: str | None = Field(None, description="Manufacturer")
    model: str | None = Field(None, description="Model")
    serial_number: str | None = Field(None, description="Serial number")
    location: str | None = Field(None, description="Location")
    status: Literal["ACTIVE", "INACTIVE", "DECOMMISSIONED"] = Field("ACTIVE", description="Lifecycle status")
    installed_at: date | None = Field(None, description="Installation date")


class EquipmentUpdate(BaseModel):
    name: str | None = Field(None, description="Display name")
    equipment_type: str | None = Field(None, description="Equipment type/category")
    manufacturer: str | None = Field(None, description="Manufacturer")
    model: str | None = Field(None, description="Model")
    serial_number: str | None = Field(None, description="Serial number")
    location: str | None = Field(None, description="Location")
    status: Literal["ACTIVE", "INACTIVE", "DECOMMISSIONED"] | None = Field(None, description="Lifecycle status")
    installed_at: date | None = Field(None, description="Installation date")


class EquipmentOut(BaseModel):
    id: int
    asset_tag: str
    name: str
    equipment_type: str | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    location: str | None
    status: Literal["ACTIVE", "INACTIVE", "DECOMMISSIONED"]
    installed_at: date | None
    created_at: datetime
    updated_at: datetime


# -----------------------
# Parameters + thresholds
# -----------------------
class ParameterCreate(BaseModel):
    code: str = Field(..., description="Unique parameter code (e.g., TEMP, VIB)")
    name: str = Field(..., description="Parameter name")
    unit: str | None = Field(None, description="Unit")
    data_type: Literal["FLOAT", "INT", "BOOL", "STRING"] = Field("FLOAT", description="Data type")
    description: str | None = Field(None, description="Description")
    is_active: bool = Field(True, description="Active flag")


class ParameterUpdate(BaseModel):
    name: str | None = Field(None, description="Parameter name")
    unit: str | None = Field(None, description="Unit")
    data_type: Literal["FLOAT", "INT", "BOOL", "STRING"] | None = Field(None, description="Data type")
    description: str | None = Field(None, description="Description")
    is_active: bool | None = Field(None, description="Active flag")


class ParameterOut(BaseModel):
    id: int
    code: str
    name: str
    unit: str | None
    data_type: Literal["FLOAT", "INT", "BOOL", "STRING"]
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ThresholdCreate(BaseModel):
    parameter_id: int = Field(..., description="Parameter ID")
    warn_low: float | None = Field(None, description="Warning low threshold")
    warn_high: float | None = Field(None, description="Warning high threshold")
    crit_low: float | None = Field(None, description="Critical low threshold")
    crit_high: float | None = Field(None, description="Critical high threshold")
    baseline_mean: float | None = Field(None, description="Baseline mean for drift detection")
    baseline_stddev: float | None = Field(None, description="Baseline standard deviation")
    window_size: int | None = Field(None, description="Window size for drift detection")
    is_active: bool = Field(True, description="Whether this threshold is active")


class ThresholdOut(BaseModel):
    id: int
    equipment_id: int
    parameter_id: int
    warn_low: float | None
    warn_high: float | None
    crit_low: float | None
    crit_high: float | None
    baseline_mean: float | None
    baseline_stddev: float | None
    window_size: int | None
    is_active: bool
    effective_from: datetime
    effective_to: datetime | None
    created_by: int | None
    created_at: datetime


# -----------------------
# Readings + alert evaluation
# -----------------------
class ReadingCreate(BaseModel):
    equipment_id: int = Field(..., description="Equipment ID")
    parameter_id: int = Field(..., description="Parameter ID")
    reading_ts: datetime = Field(..., description="Timestamp of reading")
    value_num: float | None = Field(None, description="Numeric value")
    value_text: str | None = Field(None, description="Text value (for STRING parameters)")
    source: Literal["SENSOR", "MANUAL", "CALCULATED"] = Field("SENSOR", description="Source")
    quality: Literal["GOOD", "SUSPECT", "BAD"] = Field("GOOD", description="Quality indicator")


class ReadingOut(BaseModel):
    id: int
    equipment_id: int
    parameter_id: int
    reading_ts: datetime
    value_num: float | None
    value_text: str | None
    source: Literal["SENSOR", "MANUAL", "CALCULATED"]
    quality: Literal["GOOD", "SUSPECT", "BAD"]
    recorded_by: int | None
    created_at: datetime


class AlertOut(BaseModel):
    id: int
    equipment_id: int
    parameter_id: int | None
    reading_id: int | None
    alert_ts: datetime
    severity: Literal["INFO", "WARN", "CRITICAL"]
    status: Literal["OPEN", "ACKNOWLEDGED", "RESOLVED", "SUPPRESSED"]
    title: str
    message: str | None
    rule_type: Literal["THRESHOLD", "DRIFT", "ANOMALY", "MANUAL"]
    acknowledged_by: int | None
    acknowledged_at: datetime | None
    resolved_by: int | None
    resolved_at: datetime | None
    created_at: datetime


class AlertAcknowledgeRequest(BaseModel):
    status: Literal["ACKNOWLEDGED"] = Field("ACKNOWLEDGED", description="Acknowledge the alert")


class AlertResolveRequest(BaseModel):
    status: Literal["RESOLVED"] = Field("RESOLVED", description="Resolve the alert")


# -----------------------
# Work orders + parts
# -----------------------
class WorkOrderCreate(BaseModel):
    equipment_id: int = Field(..., description="Equipment ID")
    alert_id: int | None = Field(None, description="Optional alert ID this work order addresses")
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] = Field("MEDIUM", description="Priority")
    title: str = Field(..., description="Work order title")
    description: str | None = Field(None, description="Details")
    due_date: date | None = Field(None, description="Due date")
    assigned_to: int | None = Field(None, description="User ID to assign to")


class WorkOrderUpdate(BaseModel):
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] | None = Field(None, description="Priority")
    status: Literal["OPEN", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"] | None = Field(None, description="Status")
    title: str | None = Field(None, description="Title")
    description: str | None = Field(None, description="Description")
    due_date: date | None = Field(None, description="Due date")
    assigned_to: int | None = Field(None, description="Assignee user id")


class WorkOrderOut(BaseModel):
    id: int
    equipment_id: int
    alert_id: int | None
    created_by: int | None
    assigned_to: int | None
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"]
    status: Literal["OPEN", "IN_PROGRESS", "ON_HOLD", "COMPLETED", "CANCELLED"]
    title: str
    description: str | None
    due_date: date | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkOrderTaskCreate(BaseModel):
    title: str = Field(..., description="Task title")
    description: str | None = Field(None, description="Task description")
    sort_order: int = Field(0, description="Sort order")


class WorkOrderTaskUpdate(BaseModel):
    status: Literal["TODO", "DONE", "SKIPPED"] | None = Field(None, description="Task status")
    title: str | None = Field(None, description="Title")
    description: str | None = Field(None, description="Description")
    sort_order: int | None = Field(None, description="Sort order")


class WorkOrderTaskOut(BaseModel):
    id: int
    work_order_id: int
    title: str
    description: str | None
    status: Literal["TODO", "DONE", "SKIPPED"]
    sort_order: int
    created_at: datetime
    updated_at: datetime


class PartCreate(BaseModel):
    sku: str = Field(..., description="Unique SKU")
    name: str = Field(..., description="Part name")
    description: str | None = Field(None, description="Description")
    unit_cost: Decimal = Field(Decimal("0.00"), description="Unit cost")
    quantity_on_hand: int = Field(0, description="Quantity on hand")
    reorder_level: int = Field(0, description="Reorder level")
    location: str | None = Field(None, description="Storage location")
    is_active: bool = Field(True, description="Active flag")


class PartUpdate(BaseModel):
    name: str | None = Field(None, description="Part name")
    description: str | None = Field(None, description="Description")
    unit_cost: Decimal | None = Field(None, description="Unit cost")
    quantity_on_hand: int | None = Field(None, description="Quantity on hand")
    reorder_level: int | None = Field(None, description="Reorder level")
    location: str | None = Field(None, description="Location")
    is_active: bool | None = Field(None, description="Active flag")


class PartOut(BaseModel):
    id: int
    sku: str
    name: str
    description: str | None
    unit_cost: Decimal
    quantity_on_hand: int
    reorder_level: int
    location: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WorkOrderPartUseRequest(BaseModel):
    part_id: int = Field(..., description="Part ID")
    quantity_used: int = Field(..., ge=1, description="Quantity used")


class WorkOrderPartOut(BaseModel):
    id: int
    work_order_id: int
    part_id: int
    quantity_used: int
    unit_cost_at_use: Decimal
    used_at: datetime
    used_by: int | None


class WorkOrderOutcomeCreate(BaseModel):
    outcome_code: Literal["FIXED", "MONITOR", "NO_FAULT_FOUND", "ESCALATED", "CANCELLED"] = Field(
        ..., description="Outcome code"
    )
    root_cause: str | None = Field(None, description="Root cause")
    corrective_action: str | None = Field(None, description="Corrective action")
    notes: str | None = Field(None, description="Notes")
    downtime_minutes: int | None = Field(None, ge=0, description="Downtime minutes")


class WorkOrderOutcomeOut(BaseModel):
    id: int
    work_order_id: int
    outcome_code: Literal["FIXED", "MONITOR", "NO_FAULT_FOUND", "ESCALATED", "CANCELLED"]
    root_cause: str | None
    corrective_action: str | None
    notes: str | None
    downtime_minutes: int | None
    cost_total: Decimal
    recorded_by: int | None
    recorded_at: datetime
