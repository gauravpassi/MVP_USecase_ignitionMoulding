FROM python:3.11-slim

# Install system dependencies for OpenCV (libgl1 replaces libgl1-mesa-glx on newer Debian)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi==0.115.6 \
        uvicorn[standard]==0.34.0 \
        sqlalchemy==2.0.36 \
        python-dotenv==1.0.1 \
        python-multipart==0.0.18 \
        pydantic==2.10.3 \
        opencv-python-headless==4.10.0.84 \
        numpy==1.26.4 \
        onnxruntime \
        Pillow==11.0.0 \
        requests==2.32.3

# Copy application code
COPY backend/ ./backend/
COPY storage/ ./storage/

# Create storage directories
RUN mkdir -p /app/storage/images

ENV DB_MODE=sqlite
ENV SQLITE_PATH=/app/storage/inspection.db
ENV IMAGE_STORAGE_PATH=/app/storage/images
ENV INFERENCE_MODE=opencv
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
