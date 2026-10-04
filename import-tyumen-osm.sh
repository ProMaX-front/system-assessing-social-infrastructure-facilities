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

if ! docker compose ps --status running backend | grep -q backend; then
  echo "Backend не запущен. Сначала выполните: bash start-local.sh"
  exit 1
fi

echo "Начинаю загрузку и импорт OpenStreetMap по Тюменской области."
echo "Будет скачан PBF Уральского федерального округа (несколько сотен МБ)."
echo "Импорт дорожного графа может занять продолжительное время."
echo ""

docker compose exec backend python manage.py import_osm_tyumen

echo ""
echo "Импорт завершён. Обновите страницу http://localhost:5173"
