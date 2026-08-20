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
    redis-server \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Run the service without root privileges.
RUN groupadd --system receipt && useradd --system --gid receipt --home-dir /app receipt

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy reference receipt image
COPY reference_receipt.jpg .

# Copy application code
COPY app/ ./app/
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod 755 /usr/local/bin/docker-entrypoint.sh && chown -R receipt:receipt /app
USER receipt


EXPOSE 8000

# Run Redis, the Celery worker, and the API in this container.
CMD ["/usr/local/bin/docker-entrypoint.sh"]