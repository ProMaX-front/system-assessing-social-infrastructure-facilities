from datetime import date

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand

from core.models import Normative, SocialObject


OBJECTS = [
    ("МАОУ СОШ № 15", "school", 57.1516, 65.5410, "Тюмень", 1100, "мест"),
    ("Детский сад № 87", "kindergarten", 57.1493, 65.5358, "Тюмень", 320, "мест"),
    ("Городская поликлиника", "polyclinic", 57.1582, 65.5482, "Тюмень", 800, "посещений/смену"),
    ("Областная больница", "hospital", 57.1665, 65.5580, "Тюмень", 900, "коек"),
    ("Продуктовый магазин", "shop", 57.1540, 65.5320, "Тюмень", None, ""),
    ("Остановка «Центральная»", "stop", 57.1530, 65.5384, "Тюмень", None, ""),
    ("Спортивный комплекс", "sport", 57.1464, 65.5480, "Тюмень", 500, "посетителей"),
    ("Аптека", "pharmacy", 57.1560, 65.5365, "Тюмень", None, ""),
    ("Городская библиотека", "culture", 57.1504, 65.5504, "Тюмень", None, ""),
    ("Центр социального обслуживания", "other", 57.1602, 65.5334, "Тюмень", None, ""),
]

NORMS = [
    ("school", 500),
    ("kindergarten", 500),
    ("polyclinic", 1000),
    ("shop", 500),
    ("stop", 500),
    ("sport", 1000),
    ("pharmacy", 500),
]


class Command(BaseCommand):
    help = "Создаёт демонстрационные объекты и нормативы для локальной проверки."

    def handle(self, *args, **options):
        for index, (name, category, lat, lon, address, capacity, unit) in enumerate(OBJECTS):
            SocialObject.objects.update_or_create(
                source="demo",
                source_id=str(index),
                defaults={
                    "name": name,
                    "category": category,
                    "geometry": Point(lon, lat, srid=4326),
                    "address": address,
                    "capacity": capacity,
                    "capacity_unit": unit,
                    "is_active": True,
                },
            )

        for category, distance in NORMS:
            Normative.objects.update_or_create(
                category=category,
                territory=None,
                defaults={
                    "max_distance_m": distance,
                    "movement_mode": "walking",
                    "legal_document": (
                        "СП 42.13330.2026 "
                        "(демонстрационная запись; конкретный пункт будет "
                        "верифицирован в нормативном модуле)"
                    ),
                    "valid_from": date(2026, 7, 12),
                    "priority": 100,
                },
            )

        self.stdout.write(self.style.SUCCESS("Демонстрационные данные созданы."))
