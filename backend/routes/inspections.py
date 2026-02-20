"""
/inspections endpoints — capture + inspect, list results, label.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from backend.config import IMAGE_STORAGE_PATH, INFERENCE_MODE, ONNX_MODEL_PATH
from backend.database import get_db
from backend.models.db_models import Camera, Inspection
from backend.models.schemas import InspectionOut, InspectionLabelUpdate
from backend.services.camera_manager import camera_manager
from backend.services.inference import get_inspector

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post("", response_model=InspectionOut, status_code=201)
def run_inspection(
    camera_id: str,
    mode: str = Query(default=None, description="opencv or onnx — overrides .env"),
    db: Session = Depends(get_db),
):
    """Capture image from camera, run inference, store result."""
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")

    # 1. Capture
    roi = (cam.roi_x, cam.roi_y, cam.roi_w, cam.roi_h)
    frame = camera_manager.snapshot(
        str(cam.id), cam.source_type, cam.source_uri, roi=roi,
    )
    if frame is None:
        raise HTTPException(503, "Could not capture frame from camera")

    # 2. Save image
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{cam.id}_{ts}.jpg"
    img_path = IMAGE_STORAGE_PATH / filename
    cv2.imwrite(str(img_path), frame)

    # 3. Inference
    infer_mode = mode or INFERENCE_MODE
    inspector = get_inspector(infer_mode, ONNX_MODEL_PATH)
    result = inspector.inspect(frame)

    # 4. Persist
    inspection = Inspection(
        camera_id=cam.id,
        image_path=str(img_path),
        result=result.result_str,
        defects=[d.to_dict() for d in result.defects],
        confidence=result.confidence,
        inference_mode=infer_mode,
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.post("/upload", response_model=InspectionOut, status_code=201)
def upload_and_inspect(
    file: UploadFile = File(...),
    mode: str = Query(default=None, description="opencv or onnx — overrides .env"),
    db: Session = Depends(get_db),
):
    """Upload an image file, run inference, store result (no camera needed)."""
    # 1. Read uploaded image
    contents = file.file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Could not decode image. Supported formats: jpg, png, bmp.")

    # 2. Save image to disk
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    ext = Path(file.filename).suffix if file.filename else ".jpg"
    filename = f"upload_{ts}{ext}"
    img_path = IMAGE_STORAGE_PATH / filename
    cv2.imwrite(str(img_path), frame)

    # 3. Inference
    infer_mode = mode or INFERENCE_MODE
    inspector = get_inspector(infer_mode, ONNX_MODEL_PATH)
    result = inspector.inspect(frame)

    # 4. Persist (camera_id = "upload" sentinel)
    inspection = Inspection(
        camera_id="00000000-0000-0000-0000-000000000000",
        image_path=str(img_path),
        result=result.result_str,
        defects=[d.to_dict() for d in result.defects],
        confidence=result.confidence,
        inference_mode=infer_mode,
        notes=f"Uploaded file: {file.filename}",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("", response_model=list[InspectionOut])
def list_inspections(
    camera_id: Optional[str] = None,
    result: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Inspection)
    if camera_id:
        q = q.filter(Inspection.camera_id == camera_id)
    if result:
        q = q.filter(Inspection.result == result)
    return q.order_by(Inspection.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{inspection_id}", response_model=InspectionOut)
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(404, "Inspection not found")
    return insp


@router.get("/{inspection_id}/image")
def get_inspection_image(inspection_id: str, db: Session = Depends(get_db)):
    """Return inspection image as base64."""
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(404, "Inspection not found")
    path = Path(insp.image_path)
    if not path.is_file():
        raise HTTPException(404, "Image file not found on disk")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return {"image_base64": b64}


@router.patch("/{inspection_id}/label", response_model=InspectionOut)
def label_inspection(
    inspection_id: str,
    body: InspectionLabelUpdate,
    db: Session = Depends(get_db),
):
    """Manual label (ok/ng) for dataset building."""
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(404, "Inspection not found")
    insp.label = body.label
    db.commit()
    db.refresh(insp)
    return insp
