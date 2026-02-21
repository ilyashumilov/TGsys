FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:${PYTHONPATH}

# Copy requirements and install Python dependencies
COPY services/task_result_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and shared module
COPY services/task_result_service/src/ ./src/
COPY shared ./shared

# Command
CMD ["python", "src/main.py"]
