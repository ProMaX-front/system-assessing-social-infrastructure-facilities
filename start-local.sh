#!/usr/bin/env bash
set -e

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установите и запустите Docker Desktop: https://www.docker.com/products/docker-desktop/"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker установлен, но не запущен. Откройте Docker Desktop и повторите команду."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан файл .env из .env.example"
fi

echo "Запускаю проект..."
docker compose up --build -d

echo "Ожидаю запуск backend..."
for i in {1..40}; do
  if curl -fsS http://localhost:8000/api/ >/dev/null 2>&1 || curl -fsS http://localhost:8000/admin/login/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Добавляю демонстрационные данные..."
docker compose exec -T backend python manage.py seed_demo || true

echo ""
echo "Проект запущен."
echo "Сайт: http://localhost:5173"
echo "Backend: http://localhost:8000"
echo ""
echo "Если страница ещё загружается, подождите 10-20 секунд и обновите браузер."
