FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:${PYTHONPATH}

# Copy requirements and install Python dependencies
COPY services/comment_worker_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y libglib2.0-0 && rm -rf /var/lib/apt/lists/*

# Copy source code and shared module
COPY services/comment_worker_service/src/ ./src/
COPY shared ./shared

# Command
CMD ["python", "src/main.py"]
