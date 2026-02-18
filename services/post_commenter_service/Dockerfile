FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:${PYTHONPATH}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY custom_clients ./custom_clients
COPY src ./src

CMD ["python", "src/main.py"]