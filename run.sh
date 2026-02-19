#!/bin/bash

# Останавливаем текущие контейнеры
echo "Останавливаем существующие контейнеры..."
docker-compose down

# Пересобираем образы
echo "Пересобираем образы сервисов..."
docker-compose build

# Поднимаем систему в фоне
echo "Запускаем систему в фоне..."
docker-compose up -d
# docker-compose up

echo "Система успешно перезапущена!"
docker ps