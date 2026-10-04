#!/usr/bin/env bash
set -e

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден. Установите и запустите Docker Desktop."
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

mkdir -p data/osm

echo "Запускаю проект..."
docker compose up --build -d

echo "Ожидаю запуск backend..."
for i in {1..60}; do
  if curl -fsS http://localhost:8000/admin/login/ >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Проверяю локальную учётную запись..."
docker compose exec -T backend python manage.py ensure_default_user

echo "Добавляю демонстрационные данные для первичной проверки..."
docker compose exec -T backend python manage.py seed_demo || true

echo ""
echo "Проект запущен."
echo "Сайт: http://localhost:5173"
echo "Backend: http://localhost:8000"
echo "Логин: pavel"
echo "Пароль: 12345678"
echo ""
echo "Для загрузки дорожного графа и социальных объектов OSM по Тюменской области:"
echo "  bash import-tyumen-osm.sh"
