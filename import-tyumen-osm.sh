#!/usr/bin/env bash
set -e

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker не найден."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop не запущен."
  exit 1
fi

echo "Подготавливаю backend с инструментами обработки OSM..."
docker compose build backend

# Не допускаем параллельный запуск двух django migrate:
# штатная команда backend сама выполняет migrate при старте.
docker compose stop backend >/dev/null 2>&1 || true

echo "Запускаю PostgreSQL/PostGIS..."
docker compose up -d db

echo "Ожидаю готовность базы данных..."
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

echo "Применяю миграции базы данных одним процессом..."
docker compose run --rm --no-deps backend python manage.py migrate

echo "Запускаю backend..."
docker compose up -d backend

echo ""
echo "Начинаю импорт OpenStreetMap по Тюменской области."
echo "Будут загружены:"
echo "  - автомобильный граф;"
echo "  - пешеходный граф;"
echo "  - все геометрии зданий;"
echo "  - объекты социальной инфраструктуры."
echo ""
echo "Исходный PBF Уральского федерального округа занимает несколько сотен МБ."
echo "После распаковки и загрузки в PostGIS потребуется несколько ГБ свободного места."
echo "Операция может занять продолжительное время."
echo ""

docker compose exec backend python manage.py import_osm_tyumen

echo ""
echo "Проверяю загруженные данные..."
docker compose exec -T backend python manage.py osm_status

echo ""
echo "Синхронизация OSM завершена."
