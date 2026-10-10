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
docker compose up -d db backend

echo "Применяю миграции базы данных..."
docker compose exec -T backend python manage.py migrate

echo ""
echo "Начинаю полную синхронизацию OpenStreetMap по Тюменской области."
echo "Будут загружены:"
echo "  - автомобильный граф;"
echo "  - пешеходный граф;"
echo "  - все геометрии зданий;"
echo "  - объекты социальной инфраструктуры."
echo ""
echo "Исходный PBF Уральского федерального округа занимает несколько сотен МБ."
echo "После распаковки и загрузки в PostGIS потребуется несколько ГБ свободного места."
echo "Операция выполняется один раз и может занять продолжительное время."
echo ""

docker compose exec backend python manage.py import_osm_tyumen --refresh

echo ""
echo "Проверяю загруженные данные..."
docker compose exec -T backend python manage.py osm_status

echo ""
echo "Синхронизация OSM завершена."
