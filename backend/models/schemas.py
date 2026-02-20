from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ---------- Camera ----------
class CameraCreate(BaseModel):
    name: str
    source_type: str          # "usb" or "rtsp"
    source_uri: str           # device index ("0") or rtsp://...
    roi_x: int = 0
    roi_y: int = 0
    roi_w: int = 0
    roi_h: int = 0


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source_uri: Optional[str] = None
    source_type: Optional[str] = None
    roi_x: Optional[int] = None
    roi_y: Optional[int] = None
    roi_w: Optional[int] = None
    roi_h: Optional[int] = None
    status: Optional[str] = None


class CameraOut(BaseModel):
    id: str
    name: str
    source_type: str
    source_uri: str
    roi_x: int
    roi_y: int
    roi_w: int
    roi_h: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------- Inspection ----------
class InspectionOut(BaseModel):
    id: str
    camera_id: str
    image_path: str
    result: str
    defects: list
    confidence: float
    inference_mode: str
    notes: str
    label: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InspectionLabelUpdate(BaseModel):
    label: str  # "ok" | "ng"


# ---------- Dashboard ----------
class DashboardMetrics(BaseModel):
    total_inspections: int
    pass_count: int
    fail_count: int
    pass_rate: float
    cameras_active: int
    cameras_total: int
    recent_inspections: list[InspectionOut]
    defect_breakdown: dict[str, int]
