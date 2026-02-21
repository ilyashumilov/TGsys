FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY services/comment_worker_service/Dockerfile services/comment_worker_service/Dockerfile

# Create sessions directory
RUN mkdir -p /app/sessions

# Command
CMD ["python", "src/main.py"]
