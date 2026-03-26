from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    OPERATOR = "OPERATOR"


class EquipmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DECOMMISSIONED = "DECOMMISSIONED"


class ParameterDataType(str, enum.Enum):
    FLOAT = "FLOAT"
    INT = "INT"
    BOOL = "BOOL"
    STRING = "STRING"


class ReadingSource(str, enum.Enum):
    SENSOR = "SENSOR"
    MANUAL = "MANUAL"
    CALCULATED = "CALCULATED"


class ReadingQuality(str, enum.Enum):
    GOOD = "GOOD"
    SUSPECT = "SUSPECT"
    BAD = "BAD"


class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class AlertRuleType(str, enum.Enum):
    THRESHOLD = "THRESHOLD"
    DRIFT = "DRIFT"
    ANOMALY = "ANOMALY"
    MANUAL = "MANUAL"


class WorkOrderPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class WorkOrderStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class WorkOrderTaskStatus(str, enum.Enum):
    TODO = "TODO"
    DONE = "DONE"
    SKIPPED = "SKIPPED"


class OutcomeCode(str, enum.Enum):
    FIXED = "FIXED"
    MONITOR = "MONITOR"
    NO_FAULT_FOUND = "NO_FAULT_FOUND"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.ENGINEER)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_tag: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    equipment_type: Mapped[str | None] = mapped_column(String(100))
    manufacturer: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(EquipmentStatus),
        nullable=False,
        default=EquipmentStatus.ACTIVE,
    )
    installed_at: Mapped[date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    parameters: Mapped[list["EquipmentParameter"]] = relationship(back_populates="equipment", cascade="all, delete-orphan")


class Parameter(Base):
    __tablename__ = "parameters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    data_type: Mapped[ParameterDataType] = mapped_column(
        Enum(ParameterDataType),
        nullable=False,
        default=ParameterDataType.FLOAT,
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class EquipmentParameter(Base):
    __tablename__ = "equipment_parameters"
    __table_args__ = (UniqueConstraint("equipment_id", "parameter_id", name="uq_equipment_parameter"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    parameter_id: Mapped[int] = mapped_column(ForeignKey("parameters.id", ondelete="RESTRICT"), nullable=False)
    source: Mapped[ReadingSource] = mapped_column(Enum(ReadingSource), nullable=False, default=ReadingSource.SENSOR)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sampling_seconds: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    equipment: Mapped[Equipment] = relationship(back_populates="parameters")
    parameter: Mapped[Parameter] = relationship()


class ParameterThreshold(Base):
    __tablename__ = "parameter_thresholds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    parameter_id: Mapped[int] = mapped_column(ForeignKey("parameters.id", ondelete="RESTRICT"), nullable=False)

    warn_low: Mapped[float | None] = mapped_column()
    warn_high: Mapped[float | None] = mapped_column()
    crit_low: Mapped[float | None] = mapped_column()
    crit_high: Mapped[float | None] = mapped_column()

    baseline_mean: Mapped[float | None] = mapped_column()
    baseline_stddev: Mapped[float | None] = mapped_column()
    window_size: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    effective_to: Mapped[datetime | None] = mapped_column(DateTime)

    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    equipment: Mapped[Equipment] = relationship()
    parameter: Mapped[Parameter] = relationship()
    creator: Mapped[User | None] = relationship()


class Reading(Base):
    __tablename__ = "readings"
    __table_args__ = (Index("idx_readings_eq_param_time", "equipment_id", "parameter_id", "reading_ts"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    parameter_id: Mapped[int] = mapped_column(ForeignKey("parameters.id", ondelete="RESTRICT"), nullable=False)

    reading_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    value_num: Mapped[float | None] = mapped_column()
    value_text: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[ReadingSource] = mapped_column(Enum(ReadingSource), nullable=False, default=ReadingSource.SENSOR)
    quality: Mapped[ReadingQuality] = mapped_column(Enum(ReadingQuality), nullable=False, default=ReadingQuality.GOOD)

    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    equipment: Mapped[Equipment] = relationship()
    parameter: Mapped[Parameter] = relationship()
    recorder: Mapped[User | None] = relationship()


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    parameter_id: Mapped[int | None] = mapped_column(ForeignKey("parameters.id", ondelete="SET NULL"))
    reading_id: Mapped[int | None] = mapped_column(ForeignKey("readings.id", ondelete="SET NULL"))

    alert_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), nullable=False, default=AlertStatus.OPEN)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    rule_type: Mapped[AlertRuleType] = mapped_column(Enum(AlertRuleType), nullable=False, default=AlertRuleType.THRESHOLD)

    acknowledged_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    equipment: Mapped[Equipment] = relationship()
    parameter: Mapped[Parameter | None] = relationship()
    reading: Mapped[Reading | None] = relationship()
    acknowledger: Mapped[User | None] = relationship(foreign_keys=[acknowledged_by])
    resolver: Mapped[User | None] = relationship(foreign_keys=[resolved_by])


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    priority: Mapped[WorkOrderPriority] = mapped_column(
        Enum(WorkOrderPriority),
        nullable=False,
        default=WorkOrderPriority.MEDIUM,
    )
    status: Mapped[WorkOrderStatus] = mapped_column(Enum(WorkOrderStatus), nullable=False, default=WorkOrderStatus.OPEN)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)

    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    equipment: Mapped[Equipment] = relationship()
    alert: Mapped[Alert | None] = relationship()
    creator: Mapped[User | None] = relationship(foreign_keys=[created_by])
    assignee: Mapped[User | None] = relationship(foreign_keys=[assigned_to])

    tasks: Mapped[list["WorkOrderTask"]] = relationship(back_populates="work_order", cascade="all, delete-orphan")
    parts_used: Mapped[list["WorkOrderPart"]] = relationship(back_populates="work_order", cascade="all, delete-orphan")
    outcome: Mapped["WorkOrderOutcome | None"] = relationship(back_populates="work_order", cascade="all, delete-orphan", uselist=False)


class WorkOrderTask(Base):
    __tablename__ = "work_order_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[WorkOrderTaskStatus] = mapped_column(
        Enum(WorkOrderTaskStatus),
        nullable=False,
        default=WorkOrderTaskStatus.TODO,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    work_order: Mapped[WorkOrder] = relationship(back_populates="tasks")


class Part(Base):
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    quantity_on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class WorkOrderPart(Base):
    __tablename__ = "work_order_parts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="RESTRICT"), nullable=False)

    quantity_used: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost_at_use: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    used_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    used_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    work_order: Mapped[WorkOrder] = relationship(back_populates="parts_used")
    part: Mapped[Part] = relationship()
    user: Mapped[User | None] = relationship()


class WorkOrderOutcome(Base):
    __tablename__ = "work_order_outcomes"
    __table_args__ = (UniqueConstraint("work_order_id", name="uq_outcome_wo"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False)

    outcome_code: Mapped[OutcomeCode] = mapped_column(Enum(OutcomeCode), nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text)
    corrective_action: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    downtime_minutes: Mapped[int | None] = mapped_column(Integer)
    cost_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    work_order: Mapped[WorkOrder] = relationship(back_populates="outcome")
    recorder: Mapped[User | None] = relationship()
