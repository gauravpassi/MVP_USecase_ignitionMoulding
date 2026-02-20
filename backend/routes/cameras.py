"""
/cameras endpoints — CRUD for camera definitions + live snapshot.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone

import cv2
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.db_models import Camera
from backend.models.schemas import CameraCreate, CameraUpdate, CameraOut
from backend.services.camera_manager import camera_manager

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).order_by(Camera.created_at.desc()).all()


@router.post("", response_model=CameraOut, status_code=201)
def create_camera(body: CameraCreate, db: Session = Depends(get_db)):
    cam = Camera(**body.model_dump())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(camera_id: str, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    return cam


@router.patch("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: str, body: CameraUpdate, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cam, field, value)
    cam.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=204)
def delete_camera(camera_id: str, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")
    camera_manager.close(str(cam.id))
    db.delete(cam)
    db.commit()


# ---------- Snapshot -------------------------------------------------------

@router.get("/{camera_id}/snapshot")
def snapshot(camera_id: str, db: Session = Depends(get_db)):
    """Return a JPEG snapshot as base64 (easy to embed in Streamlit)."""
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(404, "Camera not found")

    roi = (cam.roi_x, cam.roi_y, cam.roi_w, cam.roi_h)
    frame = camera_manager.snapshot(
        str(cam.id), cam.source_type, cam.source_uri, roi=roi,
    )
    if frame is None:
        raise HTTPException(503, "Could not capture frame from camera")

    _, buf = cv2.imencode(".jpg", frame)
    b64 = base64.b64encode(buf.tobytes()).decode()
    return {"image_base64": b64, "width": frame.shape[1], "height": frame.shape[0]}
