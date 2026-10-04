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

if ! grep -q '^DEFAULT_USERNAME=' .env; then
  printf '\nDEFAULT_USERNAME=Павел\n' >> .env
fi

if ! grep -Eq '^DEFAULT_PASSWORD=.+$' .env; then
  echo "Для публичного репозитория пароль не хранится в Git."
  printf "Введите пароль локальной учётной записи «Павел»: "
  stty -echo
  read -r LOCAL_PASSWORD
  stty echo
  printf '\n'
  if [ -z "$LOCAL_PASSWORD" ]; then
    echo "Пароль не может быть пустым."
    exit 1
  fi
  printf '\nDEFAULT_PASSWORD=%s\n' "$LOCAL_PASSWORD" >> .env
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

echo "Добавляю демонстрационные данные для первичной проверки..."
docker compose exec -T backend python manage.py seed_demo || true

echo ""
echo "Проект запущен."
echo "Сайт: http://localhost:5173"
echo "Backend: http://localhost:8000"
echo ""
echo "Для загрузки дорожного графа и социальных объектов OSM по Тюменской области:"
echo "  bash import-tyumen-osm.sh"
