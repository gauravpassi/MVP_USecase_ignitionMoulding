"""
/dashboard endpoints — aggregate metrics for the dashboard page.
"""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.db_models import Camera, Inspection
from backend.models.schemas import DashboardMetrics, InspectionOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics)
def dashboard_metrics(db: Session = Depends(get_db)):
    total = db.query(Inspection).count()
    pass_count = db.query(Inspection).filter(Inspection.result == "pass").count()
    fail_count = db.query(Inspection).filter(Inspection.result == "fail").count()
    pass_rate = (pass_count / total * 100) if total > 0 else 0.0

    cameras_total = db.query(Camera).count()
    cameras_active = db.query(Camera).filter(Camera.status == "active").count()

    recent = (
        db.query(Inspection)
        .order_by(Inspection.created_at.desc())
        .limit(10)
        .all()
    )

    # Defect breakdown across all fail inspections
    fails = db.query(Inspection).filter(Inspection.result == "fail").all()
    defect_counter: Counter[str] = Counter()
    for insp in fails:
        if insp.defects:
            for d in insp.defects:
                defect_counter[d.get("type", "unknown")] += 1

    return DashboardMetrics(
        total_inspections=total,
        pass_count=pass_count,
        fail_count=fail_count,
        pass_rate=round(pass_rate, 2),
        cameras_active=cameras_active,
        cameras_total=cameras_total,
        recent_inspections=[InspectionOut.model_validate(r) for r in recent],
        defect_breakdown=dict(defect_counter),
    )
