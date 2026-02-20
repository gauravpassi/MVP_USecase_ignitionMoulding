# Visual Inspection MVP — Ignition Moulding

Automated visual inspection system with camera integration, rule-based defect detection (hole/ovality/burr), and a placeholder ONNX inference pipeline.

## Architecture

```
Streamlit UI (port 8501)
    |
    v  HTTP/JSON
FastAPI Backend (port 8000)
    |
    +-- Camera Manager (OpenCV — USB + RTSP)
    +-- Inference Engine (OpenCV rules / ONNX placeholder)
    +-- PostgreSQL (cameras, inspections)
    +-- Local image storage (./storage/images/)
```

## Repo Structure

```
.
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # env-based configuration
│   ├── database.py          # SQLAlchemy engine + session
│   ├── models/
│   │   ├── db_models.py     # Camera, Inspection tables
│   │   └── schemas.py       # Pydantic request/response models
│   ├── routes/
│   │   ├── cameras.py       # /cameras, /cameras/{id}/snapshot
│   │   ├── inspections.py   # /inspections (capture + inspect)
│   │   └── dashboard.py     # /dashboard/metrics
│   └── services/
│       ├── camera_manager.py  # USB + RTSP camera handling
│       └── inference.py       # OpenCV rule-based + ONNX placeholder
├── frontend/
│   ├── app.py               # Streamlit multi-page app
│   ├── api_client.py        # HTTP helper for calling backend
│   └── pages/
│       ├── dashboard.py     # KPI cards, defect breakdown
│       ├── cameras.py       # Add/edit/delete cameras, ROI, preview
│       ├── inspect.py       # Live preview + capture & inspect
│       ├── reviews.py       # Browse past inspections, label
│       └── dataset.py       # Rapid capture for training data
├── storage/images/           # Captured inspection images
├── scripts/
│   ├── run_backend.sh
│   └── run_frontend.sh
├── docker-compose.yml        # PostgreSQL container
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker (for PostgreSQL)
- A USB webcam or RTSP IP camera (optional — the app handles missing cameras gracefully)

### 2. Start PostgreSQL

```bash
docker compose up -d
```

### 3. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work with the docker-compose Postgres)
```

### 5. Start the backend

```bash
./scripts/run_backend.sh
# or: python -m uvicorn backend.main:app --reload
```

The API is at http://localhost:8000. Docs at http://localhost:8000/docs.

### 6. Start the frontend

In a second terminal:

```bash
source .venv/bin/activate
./scripts/run_frontend.sh
# or: python -m streamlit run frontend/app.py
```

Open http://localhost:8501.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/cameras` | List all cameras |
| POST | `/cameras` | Add a camera |
| GET | `/cameras/{id}` | Get camera details |
| PATCH | `/cameras/{id}` | Update camera (name, ROI, status) |
| DELETE | `/cameras/{id}` | Remove camera |
| GET | `/cameras/{id}/snapshot` | Live snapshot (base64 JPEG) |
| POST | `/inspections?camera_id=...&mode=opencv` | Capture + inspect |
| GET | `/inspections` | List inspections (filter by camera, result) |
| GET | `/inspections/{id}` | Get single inspection |
| GET | `/inspections/{id}/image` | Get inspection image (base64) |
| PATCH | `/inspections/{id}/label` | Set manual label (ok/ng) |
| GET | `/dashboard/metrics` | Aggregated KPIs |
| GET | `/health` | Health check |

## Inference Modes

### OpenCV (default)

Rule-based contour analysis detecting:

- **Hole** — circular voids (area + circularity thresholds)
- **Ovality** — non-round features (fitted ellipse eccentricity)
- **Burr** — sharp edge protrusions (perimeter²/area ratio)

Set `INFERENCE_MODE=opencv` in `.env`.

### ONNX (placeholder)

To use a real model:

1. Export your model to ONNX format
2. Place it at the path specified in `ONNX_MODEL_PATH`
3. Set `INFERENCE_MODE=onnx` in `.env`
4. Adjust `_preprocess` and `_postprocess` in `backend/services/inference.py`

## Database Tables

**cameras**: id, name, source_type, source_uri, roi_x/y/w/h, status, timestamps

**inspections**: id, camera_id (FK), image_path, result (pass/fail), defects (JSON), confidence, inference_mode, notes, label (ok/ng), created_at
