#!/bin/bash

#!/bin/bash

# Останавливаем текущие контейнеры
echo "Останавливаем существующие контейнеры..."
docker stop $(docker ps -q --filter name=comment_worker) || true
docker-compose down

# Пересобираем образы
echo "Пересобираем образы сервисов..."
docker-compose build

# Пересобираем образ воркера
echo "Пересобираем образ воркера..."
docker build --no-cache -f services/comment_worker_service/Dockerfile -t tgsys_comment_worker_service:latest .

# Поднимаем систему в фоне
echo "Запускаем систему в фоне..."
docker-compose up -d
# docker-compose up

echo "Система успешно перезапущена!"
docker ps