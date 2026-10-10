from django.core.management.base import BaseCommand

from core.osm_import import OsmTyumenImporter


class Command(BaseCommand):
    help = (
        "Скачивает актуальные данные OpenStreetMap, формирует региональный "
        "экстракт Тюменской области и загружает в PostGIS дорожный граф, "
        "пешеходный граф, здания и объекты социальной инфраструктуры."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help=(
                "Повторно скачать исходный PBF и административную границу "
                "региона перед импортом."
            ),
        )

    def handle(self, *args, **options):
        importer = OsmTyumenImporter(stdout=self.stdout)
        run = importer.import_data(refresh=options["refresh"])

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Импорт OSM успешно завершён."
            )
        )
        self.stdout.write(f"Вершины графа: {run.nodes_count:,}")
        self.stdout.write(f"Все рёбра графа: {run.edges_count:,}")
        self.stdout.write(f"Пешеходные рёбра: {run.walk_edges_count:,}")
        self.stdout.write(f"Автомобильные рёбра: {run.drive_edges_count:,}")
        self.stdout.write(f"Геометрии зданий: {run.buildings_count:,}")
        self.stdout.write(
            f"Объекты социальной инфраструктуры: {run.social_objects_count:,}"
        )
