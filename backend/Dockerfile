# PDF Bank Statement Processor - Backend
# Uses system deps for OCR: poppler-utils, tesseract-ocr
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PDF and OCR (libgl1 = OpenGL, needed by OpenCV headless on some images)
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render/Railway set PORT; default 8000 for local Docker
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
