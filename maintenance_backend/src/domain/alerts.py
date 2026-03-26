from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from src.db.models import (
    Alert,
    AlertRuleType,
    AlertSeverity,
    AlertStatus,
    ParameterThreshold,
    Reading,
    WorkOrderPriority,
)


@dataclass(frozen=True)
class AlertDecision:
    create: bool
    severity: Optional[AlertSeverity] = None
    title: Optional[str] = None
    message: Optional[str] = None
    rule_type: AlertRuleType = AlertRuleType.THRESHOLD


def _severity_from_threshold(value: float, thresh: ParameterThreshold) -> AlertDecision:
    # Critical wins over warning; handle low/high both sides
    crit = False
    warn = False
    if thresh.crit_low is not None and value < thresh.crit_low:
        crit = True
    if thresh.crit_high is not None and value > thresh.crit_high:
        crit = True
    if thresh.warn_low is not None and value < thresh.warn_low:
        warn = True
    if thresh.warn_high is not None and value > thresh.warn_high:
        warn = True

    if crit:
        return AlertDecision(
            create=True,
            severity=AlertSeverity.CRITICAL,
            title="Critical threshold exceeded",
            message=f"Reading value {value} exceeded critical threshold.",
            rule_type=AlertRuleType.THRESHOLD,
        )
    if warn:
        return AlertDecision(
            create=True,
            severity=AlertSeverity.WARN,
            title="Warning threshold exceeded",
            message=f"Reading value {value} exceeded warning threshold.",
            rule_type=AlertRuleType.THRESHOLD,
        )
    return AlertDecision(create=False)


def _drift_decision(value: float, thresh: ParameterThreshold) -> AlertDecision:
    # Very lightweight: if baseline mean/stddev provided, alert if > mean + 3*stddev
    if thresh.baseline_mean is None or thresh.baseline_stddev is None or thresh.baseline_stddev <= 0:
        return AlertDecision(create=False)

    z = (value - thresh.baseline_mean) / thresh.baseline_stddev
    if z >= 4:
        return AlertDecision(
            create=True,
            severity=AlertSeverity.CRITICAL,
            title="Severe drift detected",
            message=f"Value drift z-score={z:.2f} (baseline mean={thresh.baseline_mean}, stddev={thresh.baseline_stddev}).",
            rule_type=AlertRuleType.DRIFT,
        )
    if z >= 3:
        return AlertDecision(
            create=True,
            severity=AlertSeverity.WARN,
            title="Drift detected",
            message=f"Value drift z-score={z:.2f} (baseline mean={thresh.baseline_mean}, stddev={thresh.baseline_stddev}).",
            rule_type=AlertRuleType.DRIFT,
        )
    return AlertDecision(create=False)


# PUBLIC_INTERFACE
def evaluate_reading_and_maybe_create_alert(db: Session, reading: Reading) -> Alert | None:
    """Evaluate a reading against the latest active thresholds and create an alert if warranted.

    Notes:
        - Uses latest active threshold record for the equipment+parameter.
        - Applies THRESHOLD rule first; then DRIFT.
        - Deduplicates by not creating another OPEN alert of same rule_type/severity for same equipment+parameter
          in the last few readings (simplified check: reuse existing OPEN alert if exists).

    Args:
        db: SQLAlchemy session
        reading: Newly created reading ORM object

    Returns:
        Alert | None: Newly created alert if decision is to create, else None.
    """
    if reading.value_num is None:
        return None

    thresh = db.execute(
        select(ParameterThreshold)
        .where(
            ParameterThreshold.equipment_id == reading.equipment_id,
            ParameterThreshold.parameter_id == reading.parameter_id,
            ParameterThreshold.is_active.is_(True),
            ParameterThreshold.effective_to.is_(None),
        )
        .order_by(desc(ParameterThreshold.id))
        .limit(1)
    ).scalar_one_or_none()

    if not thresh:
        return None

    decision = _severity_from_threshold(reading.value_num, thresh)
    if not decision.create:
        decision = _drift_decision(reading.value_num, thresh)

    if not decision.create or not decision.severity or not decision.title:
        return None

    existing_open = db.execute(
        select(Alert)
        .where(
            Alert.equipment_id == reading.equipment_id,
            Alert.parameter_id == reading.parameter_id,
            Alert.status == AlertStatus.OPEN,
            Alert.severity == decision.severity,
            Alert.rule_type == decision.rule_type,
        )
        .order_by(desc(Alert.id))
        .limit(1)
    ).scalar_one_or_none()

    if existing_open:
        return None

    alert = Alert(
        equipment_id=reading.equipment_id,
        parameter_id=reading.parameter_id,
        reading_id=reading.id,
        severity=decision.severity,
        status=AlertStatus.OPEN,
        title=decision.title,
        message=decision.message,
        rule_type=decision.rule_type,
    )
    db.add(alert)
    db.flush()  # assign id
    return alert


# PUBLIC_INTERFACE
def recommended_work_order_priority_for_alert(severity: AlertSeverity) -> WorkOrderPriority:
    """Map alert severity to recommended work order priority."""
    if severity == AlertSeverity.CRITICAL:
        return WorkOrderPriority.URGENT
    if severity == AlertSeverity.WARN:
        return WorkOrderPriority.HIGH
    return WorkOrderPriority.MEDIUM
