FROM python:3.11-slim-bookworm

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    FLAGS_enable_pir_api=0 \
    FLAGS_enable_pir_in_executor=0 \
    FLAGS_use_onednn=0 \
    PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0

# System dependencies for OpenCV + Paddle + GNU OpenMP
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy reference receipt image
COPY reference_receipt.jpg .

# Copy application code
COPY app/ ./app/


EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]