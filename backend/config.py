import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "visual_inspection")
POSTGRES_USER = os.getenv("POSTGRES_USER", "inspector")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme_secret")

# Use DATABASE_URL env var if set, otherwise build from components.
# Falls back to SQLite if DB_MODE=sqlite (no Postgres needed).
DB_MODE = os.getenv("DB_MODE", "sqlite")  # "postgres" or "sqlite"

if DB_MODE == "postgres":
    DATABASE_URL = (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
else:
    _db_path = Path(os.getenv("SQLITE_PATH", "./storage/inspection.db")).resolve()
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{_db_path}"

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

IMAGE_STORAGE_PATH = Path(os.getenv("IMAGE_STORAGE_PATH", "./storage/images"))
IMAGE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

ONNX_MODEL_PATH = os.getenv("ONNX_MODEL_PATH", "./models/defect_model.onnx")
INFERENCE_MODE = os.getenv("INFERENCE_MODE", "opencv")  # "opencv" or "onnx"
