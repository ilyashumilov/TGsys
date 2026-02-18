FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:${PYTHONPATH}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY postgres ./postgres
COPY kafka ./kafka
COPY services/channel_parser_service/src ./src

CMD ["python", "src/main.py"]

