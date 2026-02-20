FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:${PYTHONPATH}

COPY services/channel_parser_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY services/channel_parser_service/custom_clients ./custom_clients
COPY shared ./shared
COPY services/channel_parser_service/src ./src

CMD ["python", "src/main.py"]
