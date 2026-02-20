import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, TypeDecorator,
)
from sqlalchemy.orm import relationship

from backend.database import Base


# Portable UUID column — works with both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent UUID type. Stores as CHAR(36) on SQLite."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return str(value)
        return value


def _utcnow():
    return datetime.now(timezone.utc)


def _new_uuid():
    return str(uuid.uuid4())


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(GUID(), primary_key=True, default=_new_uuid)
    name = Column(String(128), nullable=False)
    source_type = Column(String(16), nullable=False)       # "usb" or "rtsp"
    source_uri = Column(String(512), nullable=False)        # device index or rtsp://...
    roi_x = Column(Integer, default=0)
    roi_y = Column(Integer, default=0)
    roi_w = Column(Integer, default=0)                      # 0 = full frame
    roi_h = Column(Integer, default=0)
    status = Column(String(16), default="active")           # active / inactive
    created_at = Column(DateTime(), default=_utcnow)
    updated_at = Column(DateTime(), default=_utcnow, onupdate=_utcnow)

    inspections = relationship("Inspection", back_populates="camera")


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(GUID(), primary_key=True, default=_new_uuid)
    camera_id = Column(GUID(), ForeignKey("cameras.id"), nullable=False)
    image_path = Column(String(512), nullable=False)
    result = Column(String(16), nullable=False)             # "pass" or "fail"
    defects = Column(JSON, default=list)                    # list of defect dicts
    confidence = Column(Float, default=0.0)
    inference_mode = Column(String(16), default="opencv")   # opencv / onnx
    notes = Column(Text, default="")
    label = Column(String(16), default="")                  # manual label: ok/ng/""
    created_at = Column(DateTime(), default=_utcnow)

    camera = relationship("Camera", back_populates="inspections")
