FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxrender1 libxext6 libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rtsp_agent.py .

# Unbuffered output so logs are visible immediately in `docker logs`
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "rtsp_agent.py"]
