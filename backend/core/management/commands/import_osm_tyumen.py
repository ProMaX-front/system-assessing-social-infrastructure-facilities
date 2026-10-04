import math
from pathlib import Path

import osmium
import requests
from django.contrib.gis.geos import LineString, Point, Polygon
from django.core.management.base import BaseCommand

from core.models import RoadEdge, RoadNode, SocialObject


GEOFABRIK_URL = "https://download.geofabrik.de/russia/ural-fed-district-latest.osm.pbf"
DEFAULT_PBF = Path("/data/osm/ural-fed-district-latest.osm.pbf")

# Границы охвата юга Тюменской области для первичной загрузки.
# Источник границ охвата: картографические параметры Тюменской области.
TYUMEN_BBOX = (64.3, 54.8, 75.5, 60.5)  # min_lon, min_lat, max_lon, max_lat

WALKING_BLOCKED_HIGHWAYS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "raceway",
}


def haversine_m(lon1, lat1, lon2, lat2):
    radius = 6_371_008.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def in_bbox(lon, lat):
    min_lon, min_lat, max_lon, max_lat = TYUMEN_BBOX
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def tag(tags, key, default=""):
    value = tags.get(key)
    return value if value is not None else default


def classify_social(tags):
    amenity = tag(tags, "amenity")
    leisure = tag(tags, "leisure")
    tourism = tag(tags, "tourism")
    highway = tag(tags, "highway")
    public_transport = tag(tags, "public_transport")
    shop = tag(tags, "shop")

    if amenity == "school":
        return "school", "amenity=school"
    if amenity == "kindergarten":
        return "kindergarten", "amenity=kindergarten"
    if amenity in {"clinic", "doctors"}:
        return "polyclinic", f"amenity={amenity}"
    if amenity == "hospital":
        return "hospital", "amenity=hospital"
    if amenity == "pharmacy":
        return "pharmacy", "amenity=pharmacy"
    if shop:
        return "shop", f"shop={shop}"
    if highway == "bus_stop" or public_transport in {"platform", "stop_position"}:
        return "stop", f"public_transport={public_transport or highway}"
    if leisure in {"sports_centre", "stadium", "pitch", "swimming_pool", "fitness_centre"}:
        return "sport", f"leisure={leisure}"
    if amenity in {"library", "theatre", "cinema", "arts_centre", "community_centre"}:
        return "culture", f"amenity={amenity}"
    if tourism == "museum":
        return "culture", "tourism=museum"
    if amenity == "social_facility":
        return "other", "amenity=social_facility"
    return None, ""


def make_name(tags, category):
    return (
        tag(tags, "name:ru")
        or tag(tags, "name")
        or tag(tags, "official_name")
        or dict(SocialObject.Category.choices).get(category, "Социальный объект")
    )


def make_address(tags):
    parts = [
        tag(tags, "addr:city"),
        tag(tags, "addr:street"),
        tag(tags, "addr:housenumber"),
    ]
    return ", ".join(part for part in parts if part)


def is_walkable(tags, highway):
    if highway in WALKING_BLOCKED_HIGHWAYS:
        return False
    if tag(tags, "foot") in {"no", "private"}:
        return False
    if tag(tags, "access") in {"no", "private"} and tag(tags, "foot") not in {"yes", "designated", "permissive"}:
        return False
    return True


class TyumenOsmHandler(osmium.SimpleHandler):
    def __init__(self, command):
        super().__init__()
        self.command = command
        self.road_nodes = {}
        self.road_edges = []
        self.social_objects = []
        self.ways_seen = 0
        self.roads_created = 0
        self.objects_created = 0

    def _flush_roads(self):
        if self.road_nodes:
            RoadNode.objects.bulk_create(
                list(self.road_nodes.values()),
                batch_size=5000,
                ignore_conflicts=True,
            )
            self.road_nodes.clear()

        if self.road_edges:
            RoadEdge.objects.bulk_create(
                self.road_edges,
                batch_size=5000,
                ignore_conflicts=True,
            )
            self.roads_created += len(self.road_edges)
            self.road_edges.clear()

    def _flush_objects(self):
        if self.social_objects:
            SocialObject.objects.bulk_create(
                self.social_objects,
                batch_size=2000,
            )
            self.objects_created += len(self.social_objects)
            self.social_objects.clear()

    def node(self, node):
        if not node.location.valid():
            return
        lon = node.location.lon
        lat = node.location.lat
        if not in_bbox(lon, lat):
            return

        category, subcategory = classify_social(node.tags)
        if not category:
            return

        self.social_objects.append(
            SocialObject(
                name=make_name(node.tags, category),
                category=category,
                subcategory=subcategory,
                address=make_address(node.tags),
                geometry=Point(lon, lat, srid=4326),
                source="osm",
                source_id=f"node/{node.id}",
                is_active=True,
            )
        )
        if len(self.social_objects) >= 2000:
            self._flush_objects()

    def way(self, way):
        self.ways_seen += 1
        if self.ways_seen % 100_000 == 0:
            self.command.stdout.write(
                f"Обработано OSM ways: {self.ways_seen:,}; "
                f"сегментов дорог: {self.roads_created:,}; "
                f"соцобъектов: {self.objects_created:,}"
            )

        coords = []
        node_refs = []
        for node_ref in way.nodes:
            if not node_ref.location.valid():
                continue
            coords.append((node_ref.location.lon, node_ref.location.lat))
            node_refs.append(node_ref.ref)

        if len(coords) < 2 or not any(in_bbox(lon, lat) for lon, lat in coords):
            return

        highway = tag(way.tags, "highway")
        if highway:
            oneway = tag(way.tags, "oneway") in {"yes", "1", "true"}
            walkable = is_walkable(way.tags, highway)
            road_name = tag(way.tags, "name:ru") or tag(way.tags, "name")

            for index in range(len(coords) - 1):
                lon1, lat1 = coords[index]
                lon2, lat2 = coords[index + 1]
                if not (in_bbox(lon1, lat1) or in_bbox(lon2, lat2)):
                    continue

                source_id = int(node_refs[index])
                target_id = int(node_refs[index + 1])
                self.road_nodes[source_id] = RoadNode(
                    osm_id=source_id,
                    geometry=Point(lon1, lat1, srid=4326),
                )
                self.road_nodes[target_id] = RoadNode(
                    osm_id=target_id,
                    geometry=Point(lon2, lat2, srid=4326),
                )
                self.road_edges.append(
                    RoadEdge(
                        osm_way_id=int(way.id),
                        segment_index=index,
                        source_osm_id=source_id,
                        target_osm_id=target_id,
                        geometry=LineString((lon1, lat1), (lon2, lat2), srid=4326),
                        length_m=haversine_m(lon1, lat1, lon2, lat2),
                        highway=highway[:64],
                        name=road_name[:255],
                        oneway=oneway,
                        walkable=walkable,
                    )
                )

                if len(self.road_edges) >= 5000:
                    self._flush_roads()

        category, subcategory = classify_social(way.tags)
        if category:
            inside_coords = [(lon, lat) for lon, lat in coords if in_bbox(lon, lat)]
            if not inside_coords:
                return

            footprint = None
            point = None
            if len(coords) >= 4 and coords[0] == coords[-1]:
                try:
                    footprint = Polygon(coords, srid=4326)
                    point = footprint.centroid
                except Exception:
                    footprint = None

            if point is None:
                avg_lon = sum(lon for lon, _ in inside_coords) / len(inside_coords)
                avg_lat = sum(lat for _, lat in inside_coords) / len(inside_coords)
                point = Point(avg_lon, avg_lat, srid=4326)

            self.social_objects.append(
                SocialObject(
                    name=make_name(way.tags, category),
                    category=category,
                    subcategory=subcategory,
                    address=make_address(way.tags),
                    geometry=point,
                    footprint=footprint,
                    source="osm",
                    source_id=f"way/{way.id}",
                    is_active=True,
                )
            )
            if len(self.social_objects) >= 2000:
                self._flush_objects()

    def finish(self):
        self._flush_roads()
        self._flush_objects()


class Command(BaseCommand):
    help = (
        "Загружает актуальный OSM PBF Уральского ФО и импортирует дорожный граф "
        "и социальные объекты в пределах охвата Тюменской области."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pbf",
            default=str(DEFAULT_PBF),
            help="Путь к локальному .osm.pbf. Если файла нет, он будет скачан.",
        )
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help="Не удалять ранее импортированные OSM дороги и объекты.",
        )

    def _download(self, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f"Скачиваю OSM: {GEOFABRIK_URL}")
        with requests.get(
            GEOFABRIK_URL,
            stream=True,
            timeout=(30, 600),
            headers={
                "User-Agent": "social-infrastructure-gis/0.1 (academic open-source project)"
            },
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            with target.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    output.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        percent = downloaded * 100 / total
                        self.stdout.write(
                            f"Загружено {downloaded / 1024 / 1024:.0f} МБ "
                            f"из {total / 1024 / 1024:.0f} МБ ({percent:.0f}%)",
                            ending="\r",
                        )
        self.stdout.write("")

    def handle(self, *args, **options):
        pbf_path = Path(options["pbf"])
        if not pbf_path.exists():
            self._download(pbf_path)

        if not options["keep_existing"]:
            self.stdout.write("Очищаю предыдущий OSM-граф и OSM-объекты...")
            RoadEdge.objects.all().delete()
            RoadNode.objects.all().delete()
            SocialObject.objects.filter(source="osm").delete()

        self.stdout.write(
            "Импортирую дорожный граф и социальные объекты. "
            "Для полного файла Уральского ФО операция может занять продолжительное время."
        )

        handler = TyumenOsmHandler(self)
        handler.apply_file(str(pbf_path), locations=True)
        handler.finish()

        self.stdout.write(
            self.style.SUCCESS(
                f"Импорт завершён. Дорожных сегментов: {handler.roads_created:,}; "
                f"социальных объектов: {handler.objects_created:,}."
            )
        )
