from django.core.management.base import BaseCommand

from core.models import OsmBuilding, OsmImportRun, RoadEdge, RoadNode, SocialObject


class Command(BaseCommand):
    help = "Показывает состояние локальной базы геоданных OSM."

    def handle(self, *args, **options):
        latest = OsmImportRun.objects.first()

        self.stdout.write("Состояние базы геоданных OSM")
        self.stdout.write("=" * 38)

        if latest:
            self.stdout.write(
                f"Последний импорт: {latest.started_at:%d.%m.%Y %H:%M}"
            )
            self.stdout.write(f"Статус: {latest.get_status_display()}")
            if latest.source_timestamp:
                self.stdout.write(
                    f"Дата исходных данных: "
                    f"{latest.source_timestamp:%d.%m.%Y %H:%M}"
                )
            if latest.error_message:
                self.stdout.write(f"Ошибка: {latest.error_message}")
        else:
            self.stdout.write("Импорт OSM ещё не выполнялся.")

        self.stdout.write("")
        self.stdout.write(f"Вершины графа: {RoadNode.objects.count():,}")
        self.stdout.write(f"Рёбра графа: {RoadEdge.objects.count():,}")
        self.stdout.write(
            f"Пешеходные рёбра: "
            f"{RoadEdge.objects.filter(walkable=True).count():,}"
        )
        self.stdout.write(
            f"Автомобильные рёбра: "
            f"{RoadEdge.objects.filter(drivable=True).count():,}"
        )
        self.stdout.write(f"Здания OSM: {OsmBuilding.objects.count():,}")
        self.stdout.write(
            f"Объекты инфраструктуры OSM: "
            f"{SocialObject.objects.filter(source='osm').count():,}"
        )

        self.stdout.write("")
        self.stdout.write("Объекты инфраструктуры по категориям:")
        for category, label in SocialObject.Category.choices:
            count = SocialObject.objects.filter(
                source="osm",
                category=category,
            ).count()
            self.stdout.write(f"  {label}: {count:,}")

        self.stdout.write("")
        self.stdout.write("Здания инфраструктуры по категориям:")
        for category, label in SocialObject.Category.choices:
            count = OsmBuilding.objects.filter(
                infrastructure_category=category,
            ).count()
            self.stdout.write(f"  {label}: {count:,}")
