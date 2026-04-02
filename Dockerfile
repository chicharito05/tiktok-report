FROM python:3.11-slim

WORKDIR /app

# WeasyPrint system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libcairo2 libglib2.0-0 shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ ./worker/
COPY templates/ ./templates/
COPY config/ ./config/

EXPOSE 8787

CMD ["uvicorn", "worker.api_server:app", "--host", "0.0.0.0", "--port", "8787"]
