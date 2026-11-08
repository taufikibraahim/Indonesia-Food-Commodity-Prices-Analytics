FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY batch_ingest.py .

COPY dataset/ ./dataset/

CMD ["python", "batch_ingest.py"]