FROM python:3.12-slim

# System deps for insightface / OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake libglib2.0-0 libsm6 libxrender1 libxext6 \
    libgl1-mesa-glx libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /app/storage/faces /app/storage/snapshots

# Pre-download InsightFace buffalo_l model (so container start is fast)
# This runs at build time; if network unavailable, remove this line and
# the model will download on first inference request instead.
RUN python -c "from insightface.app import FaceAnalysis; a=FaceAnalysis(name='buffalo_l'); a.prepare(ctx_id=-1,det_size=(640,640))" || true

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
