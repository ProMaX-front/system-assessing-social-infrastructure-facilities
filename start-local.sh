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

echo "Собираю контейнеры..."
docker compose build

# Выполняем миграции строго одним процессом до запуска backend.
docker compose stop backend >/dev/null 2>&1 || true
docker compose up -d db

echo "Ожидаю готовность PostgreSQL/PostGIS..."
for i in {1..60}; do
  if docker compose exec -T db pg_isready       -U "${POSTGRES_USER:-infrastructure}"       -d "${POSTGRES_DB:-infrastructure}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Проверяю целостность незавершённых миграций..."
docker compose exec -T db psql \
  -U "${POSTGRES_USER:-infrastructure}" \
  -d "${POSTGRES_DB:-infrastructure}" \
  -v ON_ERROR_STOP=1 \
  -c "DO \$\$ BEGIN
        IF to_regclass('public.core_osmimportrun') IS NULL
           AND to_regclass('public.core_osmimportrun_id_seq') IS NOT NULL THEN
          DROP SEQUENCE public.core_osmimportrun_id_seq CASCADE;
        END IF;
      END \$\$;"

echo "Применяю миграции..."
docker compose run --rm --no-deps backend python manage.py migrate

echo "Запускаю проект..."
docker compose up -d backend frontend

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
