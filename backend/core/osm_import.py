import json
import math
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import osmium
import requests
from django.contrib.gis.geos import GEOSGeometry, LineString, MultiPolygon, Point
from django.utils import timezone

from .models import (
    AdministrativeUnit,
    OsmBuilding,
    OsmImportRun,
    RoadEdge,
    RoadNode,
    SocialObject,
)


GEOFABRIK_URL = "https://download.geofabrik.de/russia/ural-fed-district-latest.osm.pbf"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
REGION_QUERY = "Тюменская область, Россия"

DATA_DIR = Path("/data/osm")
SOURCE_PBF = DATA_DIR / "ural-fed-district-latest.osm.pbf"
REGION_BOUNDARY = DATA_DIR / "tyumen-oblast.geojson"
REGION_PBF = DATA_DIR / "tyumen-oblast.osm.pbf"

USER_AGENT = (
    "social-infrastructure-gis/0.2 "
    "(academic project; OpenStreetMap data importer)"
)

WALK_BLOCKED_HIGHWAYS = {
    "motorway",
    "motorway_link",
    "raceway",
    "construction",
    "proposed",
}

DRIVE_BLOCKED_HIGHWAYS = {
    "footway",
    "path",
    "pedestrian",
    "steps",
    "cycleway",
    "bridleway",
    "corridor",
    "platform",
    "elevator",
    "construction",
    "proposed",
}

DENIED_ACCESS = {"no", "private"}
ALLOWED_ACCESS = {"yes", "designated", "permissive", "destination", "customers"}


def _tag(tags, key, default=""):
    value = tags.get(key)
    return value if value is not None else default


def _tags_dict(tags):
    return {item.k: item.v for item in tags}


def _is_truthy_osm(value):
    return str(value).lower() not in {"", "no", "false", "0"}


def _address(tags):
    parts = [
        _tag(tags, "addr:city"),
        _tag(tags, "addr:place"),
        _tag(tags, "addr:street"),
        _tag(tags, "addr:housenumber"),
    ]
    return ", ".join(dict.fromkeys(part for part in parts if part))


def _name(tags, category=""):
    labels = dict(SocialObject.Category.choices)
    return (
        _tag(tags, "name:ru")
        or _tag(tags, "name")
        or _tag(tags, "official_name")
        or labels.get(category, "")
    )


def classify_infrastructure(tags):
    amenity = _tag(tags, "amenity")
    building = _tag(tags, "building")
    leisure = _tag(tags, "leisure")
    tourism = _tag(tags, "tourism")
    highway = _tag(tags, "highway")
    public_transport = _tag(tags, "public_transport")
    railway = _tag(tags, "railway")
    shop = _tag(tags, "shop")

    if amenity == "school" or building == "school":
        return SocialObject.Category.SCHOOL, "образование: школа"
    if amenity == "kindergarten" or building == "kindergarten":
        return SocialObject.Category.KINDERGARTEN, "образование: детский сад"
    if amenity in {"college"} or building in {"college"}:
        return SocialObject.Category.COLLEGE, "образование: колледж / техникум"
    if amenity in {"university"} or building in {"university"}:
        return SocialObject.Category.UNIVERSITY, "образование: вуз"

    if amenity in {"clinic", "doctors", "dentist"} or building in {"clinic"}:
        return SocialObject.Category.POLYCLINIC, f"здравоохранение: {amenity or building}"
    if amenity == "hospital" or building == "hospital":
        return SocialObject.Category.HOSPITAL, "здравоохранение: больница"
    if amenity == "pharmacy":
        return SocialObject.Category.PHARMACY, "здравоохранение: аптека"

    if shop:
        return SocialObject.Category.SHOP, f"торговля: {shop}"

    if (
        highway == "bus_stop"
        or amenity == "bus_station"
        or public_transport in {"platform", "stop_position", "station"}
        or railway in {"station", "halt", "tram_stop"}
    ):
        return SocialObject.Category.STOP, "общественный транспорт"

    if (
        leisure
        in {
            "sports_centre",
            "stadium",
            "pitch",
            "swimming_pool",
            "fitness_centre",
            "sports_hall",
        }
        or amenity in {"dojo"}
        or building in {"stadium", "sports_hall"}
    ):
        return SocialObject.Category.SPORT, f"спорт: {leisure or amenity or building}"

    if amenity in {
        "library",
        "theatre",
        "cinema",
        "arts_centre",
        "community_centre",
        "music_school",
    }:
        return SocialObject.Category.CULTURE, f"культура: {amenity}"
    if tourism in {"museum", "gallery"}:
        return SocialObject.Category.CULTURE, f"культура: {tourism}"

    if amenity in {
        "social_facility",
        "nursing_home",
        "social_centre",
    }:
        return SocialObject.Category.SOCIAL, f"социальное обслуживание: {amenity}"

    return None, ""


def _walking_access(tags, highway):
    foot = _tag(tags, "foot")
    access = _tag(tags, "access")

    if foot in ALLOWED_ACCESS:
        return True
    if foot in DENIED_ACCESS:
        return False
    if access in DENIED_ACCESS:
        return False
    return highway not in WALK_BLOCKED_HIGHWAYS


def _driving_access(tags, highway):
    specific = (
        _tag(tags, "motor_vehicle")
        or _tag(tags, "motorcar")
        or _tag(tags, "vehicle")
    )
    access = _tag(tags, "access")

    if specific in ALLOWED_ACCESS:
        return highway not in DRIVE_BLOCKED_HIGHWAYS
    if specific in DENIED_ACCESS:
        return False
    if access in DENIED_ACCESS:
        return False
    return highway not in DRIVE_BLOCKED_HIGHWAYS


def _directions(tags, walkable, drivable):
    drive_forward = drivable
    drive_backward = drivable
    walk_forward = walkable
    walk_backward = walkable

    oneway = _tag(tags, "oneway")
    junction = _tag(tags, "junction")

    if drivable and (oneway in {"yes", "1", "true"} or junction == "roundabout"):
        drive_backward = False
    elif drivable and oneway == "-1":
        drive_forward = False

    foot_oneway = _tag(tags, "oneway:foot")
    if walkable and foot_oneway in {"yes", "1", "true"}:
        walk_backward = False
    elif walkable and foot_oneway == "-1":
        walk_forward = False

    return walk_forward, walk_backward, drive_forward, drive_backward


def _haversine_m(lon1, lat1, lon2, lat2):
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


class OsmTyumenImporter:
    def __init__(self, stdout=None):
        self.stdout = stdout
        self.wkt_factory = osmium.geom.WKTFactory()

        self.graph_nodes = {}
        self.walk_node_ids = set()
        self.drive_node_ids = set()
        self.graph_edges = []
        self.social_objects = []
        self.buildings = []

        self.objects_seen = 0
        self.edges_buffered = 0
        self.social_buffered = 0
        self.buildings_buffered = 0

        self.boundary = None
        self.boundary_prepared = None
        self.import_run = None

    def log(self, message, ending=None):
        if self.stdout:
            kwargs = {}
            if ending is not None:
                kwargs["ending"] = ending
            self.stdout.write(message, **kwargs)

    def _download(self, url, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        self.log(f"Скачивание исходных данных OSM: {url}")
        headers = {"User-Agent": USER_AGENT}
        source_timestamp = None

        with requests.get(
            url,
            stream=True,
            timeout=(30, 900),
            headers=headers,
        ) as response:
            response.raise_for_status()
            last_modified = response.headers.get("Last-Modified")
            if last_modified:
                try:
                    source_timestamp = parsedate_to_datetime(last_modified)
                except (TypeError, ValueError):
                    source_timestamp = None

            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            with target.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    output.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        self.log(
                            f"Загружено {downloaded / 1024 / 1024:.0f} МБ "
                            f"из {total / 1024 / 1024:.0f} МБ "
                            f"({downloaded * 100 / total:.0f}%)",
                            ending="\r",
                        )
        self.log("")
        return source_timestamp

    def _load_boundary(self, refresh=False):
        if refresh and REGION_BOUNDARY.exists():
            REGION_BOUNDARY.unlink()

        if not REGION_BOUNDARY.exists():
            self.log("Получение точной административной границы Тюменской области из OSM...")
            response = requests.get(
                NOMINATIM_URL,
                params={
                    "q": REGION_QUERY,
                    "format": "jsonv2",
                    "polygon_geojson": 1,
                    "limit": 1,
                    "countrycodes": "ru",
                    "featuretype": "state",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=(20, 120),
            )
            response.raise_for_status()
            results = response.json()
            if not results:
                raise RuntimeError(
                    "Не удалось получить границу Тюменской области из OSM."
                )

            geometry = results[0].get("geojson")
            if not geometry or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
                raise RuntimeError(
                    "OSM вернул некорректную геометрию границы Тюменской области."
                )

            REGION_BOUNDARY.parent.mkdir(parents=True, exist_ok=True)
            REGION_BOUNDARY.write_text(
                json.dumps(
                    {
                        "type": "Feature",
                        "properties": {
                            "name": "Тюменская область",
                            "source": "OpenStreetMap / Nominatim",
                        },
                        "geometry": geometry,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        feature = json.loads(REGION_BOUNDARY.read_text(encoding="utf-8"))
        geometry = GEOSGeometry(
            json.dumps(feature["geometry"], ensure_ascii=False),
            srid=4326,
        )
        if geometry.geom_type == "Polygon":
            geometry = MultiPolygon(geometry, srid=4326)
        if geometry.geom_type != "MultiPolygon":
            raise RuntimeError("Граница региона должна быть Polygon или MultiPolygon.")

        self.boundary = geometry
        self.boundary_prepared = geometry.prepared

        AdministrativeUnit.objects.update_or_create(
            name="Тюменская область",
            unit_type=AdministrativeUnit.UnitType.REGION,
            defaults={"geometry": geometry},
        )

    def _prepare_files(self, refresh=False):
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        source_timestamp = None
        if refresh and SOURCE_PBF.exists():
            SOURCE_PBF.unlink()
        if refresh and REGION_PBF.exists():
            REGION_PBF.unlink()

        if not SOURCE_PBF.exists():
            source_timestamp = self._download(GEOFABRIK_URL, SOURCE_PBF)

        if source_timestamp is None:
            source_timestamp = datetime.fromtimestamp(
                SOURCE_PBF.stat().st_mtime,
                tz=timezone.utc,
            )

        if (
            not REGION_PBF.exists()
            or REGION_PBF.stat().st_mtime < SOURCE_PBF.stat().st_mtime
            or REGION_PBF.stat().st_mtime < REGION_BOUNDARY.stat().st_mtime
        ):
            self.log(
                "Формирование регионального PBF по точной границе "
                "Тюменской области..."
            )
            subprocess.run(
                [
                    "osmium",
                    "extract",
                    "--polygon",
                    str(REGION_BOUNDARY),
                    "--strategy",
                    "smart",
                    "--overwrite",
                    str(SOURCE_PBF),
                    "-o",
                    str(REGION_PBF),
                ],
                check=True,
            )

        return source_timestamp

    def _inside_region(self, point):
        return self.boundary_prepared.covers(point)

    def _segment_inside_region(self, lon1, lat1, lon2, lat2):
        midpoint = Point((lon1 + lon2) / 2, (lat1 + lat2) / 2, srid=4326)
        return self._inside_region(midpoint)

    def _flush_graph(self):
        if self.graph_nodes:
            RoadNode.objects.bulk_create(
                list(self.graph_nodes.values()),
                batch_size=5000,
                ignore_conflicts=True,
            )
            node_ids = list(self.graph_nodes.keys())
            walk_ids = [node_id for node_id in node_ids if node_id in self.walk_node_ids]
            drive_ids = [node_id for node_id in node_ids if node_id in self.drive_node_ids]

            if walk_ids:
                RoadNode.objects.filter(osm_id__in=walk_ids).update(walkable=True)
            if drive_ids:
                RoadNode.objects.filter(osm_id__in=drive_ids).update(drivable=True)

            self.graph_nodes.clear()
            self.walk_node_ids.clear()
            self.drive_node_ids.clear()

        if self.graph_edges:
            RoadEdge.objects.bulk_create(self.graph_edges, batch_size=5000)
            self.graph_edges.clear()

    def _flush_social(self):
        if self.social_objects:
            SocialObject.objects.bulk_create(
                self.social_objects,
                batch_size=2000,
            )
            self.social_objects.clear()

    def _flush_buildings(self):
        if self.buildings:
            OsmBuilding.objects.bulk_create(
                self.buildings,
                batch_size=1000,
            )
            self.buildings.clear()

    def _buffer_social_node(self, obj, tags):
        category, subcategory = classify_infrastructure(tags)
        if not category or not obj.location.valid():
            return

        point = Point(obj.location.lon, obj.location.lat, srid=4326)
        if not self._inside_region(point):
            return

        self.social_objects.append(
            SocialObject(
                name=_name(tags, category),
                category=category,
                subcategory=subcategory,
                address=_address(tags),
                geometry=point,
                source="osm",
                source_id=f"node/{obj.id}",
                osm_type="node",
                osm_id=int(obj.id),
                osm_tags=tags,
                import_run=self.import_run,
                is_active=True,
            )
        )
        self.social_buffered += 1
        if len(self.social_objects) >= 2000:
            self._flush_social()

    def _buffer_linear_stop(self, obj, tags):
        category, subcategory = classify_infrastructure(tags)
        if category != SocialObject.Category.STOP or obj.is_closed():
            return

        coords = [
            (node.location.lon, node.location.lat)
            for node in obj.nodes
            if node.location.valid()
        ]
        if len(coords) < 2:
            return

        lon = sum(value[0] for value in coords) / len(coords)
        lat = sum(value[1] for value in coords) / len(coords)
        point = Point(lon, lat, srid=4326)
        if not self._inside_region(point):
            return

        self.social_objects.append(
            SocialObject(
                name=_name(tags, category),
                category=category,
                subcategory=subcategory,
                address=_address(tags),
                geometry=point,
                source="osm",
                source_id=f"way/{obj.id}",
                osm_type="way",
                osm_id=int(obj.id),
                osm_tags=tags,
                import_run=self.import_run,
                is_active=True,
            )
        )
        self.social_buffered += 1
        if len(self.social_objects) >= 2000:
            self._flush_social()

    def _buffer_graph_way(self, obj, tags):
        highway = _tag(tags, "highway")
        if not highway:
            return

        walkable = _walking_access(tags, highway)
        drivable = _driving_access(tags, highway)
        if not walkable and not drivable:
            return

        (
            walk_forward,
            walk_backward,
            drive_forward,
            drive_backward,
        ) = _directions(tags, walkable, drivable)

        coords = []
        refs = []
        for node in obj.nodes:
            if node.location.valid():
                coords.append((node.location.lon, node.location.lat))
                refs.append(int(node.ref))

        if len(coords) < 2:
            return

        for index in range(len(coords) - 1):
            lon1, lat1 = coords[index]
            lon2, lat2 = coords[index + 1]
            if not self._segment_inside_region(lon1, lat1, lon2, lat2):
                continue

            source_id = refs[index]
            target_id = refs[index + 1]

            self.graph_nodes[source_id] = RoadNode(
                osm_id=source_id,
                geometry=Point(lon1, lat1, srid=4326),
                import_run=self.import_run,
            )
            self.graph_nodes[target_id] = RoadNode(
                osm_id=target_id,
                geometry=Point(lon2, lat2, srid=4326),
                import_run=self.import_run,
            )

            if walkable:
                self.walk_node_ids.update((source_id, target_id))
            if drivable:
                self.drive_node_ids.update((source_id, target_id))

            oneway = drive_forward != drive_backward
            self.graph_edges.append(
                RoadEdge(
                    osm_way_id=int(obj.id),
                    segment_index=index,
                    source_osm_id=source_id,
                    target_osm_id=target_id,
                    geometry=LineString(
                        (lon1, lat1),
                        (lon2, lat2),
                        srid=4326,
                    ),
                    length_m=_haversine_m(lon1, lat1, lon2, lat2),
                    highway=highway[:64],
                    name=(_tag(tags, "name:ru") or _tag(tags, "name"))[:255],
                    surface=_tag(tags, "surface")[:64],
                    access=_tag(tags, "access")[:64],
                    foot=_tag(tags, "foot")[:64],
                    motor_vehicle=(
                        _tag(tags, "motor_vehicle")
                        or _tag(tags, "motorcar")
                        or _tag(tags, "vehicle")
                    )[:64],
                    oneway=oneway,
                    walkable=walkable,
                    drivable=drivable,
                    walk_forward=walk_forward,
                    walk_backward=walk_backward,
                    drive_forward=drive_forward,
                    drive_backward=drive_backward,
                    bridge=_is_truthy_osm(_tag(tags, "bridge")),
                    tunnel=_is_truthy_osm(_tag(tags, "tunnel")),
                    osm_tags=tags,
                    import_run=self.import_run,
                )
            )
            self.edges_buffered += 1

            if len(self.graph_edges) >= 5000:
                self._flush_graph()

    def _buffer_area(self, obj, tags):
        category, subcategory = classify_infrastructure(tags)
        building_type = _tag(tags, "building")
        is_building = bool(building_type and building_type != "no")

        if not category and not is_building:
            return

        try:
            wkt = self.wkt_factory.create_multipolygon(obj)
            geometry = GEOSGeometry(wkt, srid=4326)
        except Exception:
            return

        if geometry.empty or not geometry.valid:
            return
        if geometry.geom_type == "Polygon":
            geometry = MultiPolygon(geometry, srid=4326)
        if geometry.geom_type != "MultiPolygon":
            return
        if not self.boundary_prepared.intersects(geometry):
            return

        source_type = "way" if obj.from_way() else "relation"
        source_id = int(obj.orig_id())
        point = geometry.point_on_surface

        if is_building:
            self.buildings.append(
                OsmBuilding(
                    osm_type=source_type,
                    osm_id=source_id,
                    name=_name(tags, category),
                    address=_address(tags),
                    building_type=building_type[:128],
                    infrastructure_category=category or "",
                    geometry=geometry,
                    centroid=point,
                    osm_tags=tags,
                    import_run=self.import_run,
                )
            )
            self.buildings_buffered += 1
            if len(self.buildings) >= 1000:
                self._flush_buildings()

        if category:
            self.social_objects.append(
                SocialObject(
                    name=_name(tags, category),
                    category=category,
                    subcategory=subcategory,
                    address=_address(tags),
                    geometry=point,
                    footprint=geometry,
                    source="osm",
                    source_id=f"{source_type}/{source_id}",
                    osm_type=source_type,
                    osm_id=source_id,
                    osm_tags=tags,
                    import_run=self.import_run,
                    is_active=True,
                )
            )
            self.social_buffered += 1
            if len(self.social_objects) >= 2000:
                self._flush_social()

    def _clear_osm_data(self):
        self.log("Очистка ранее импортированных данных OSM...")
        RoadEdge.objects.all().delete()
        RoadNode.objects.all().delete()
        OsmBuilding.objects.all().delete()
        SocialObject.objects.filter(source="osm").delete()

    def import_data(self, refresh=False):
        self._load_boundary(refresh=refresh)
        source_timestamp = self._prepare_files(refresh=refresh)

        self.import_run = OsmImportRun.objects.create(
            region_name="Тюменская область",
            source_url=GEOFABRIK_URL,
            source_file=str(REGION_PBF),
            source_timestamp=source_timestamp,
            status=OsmImportRun.Status.RUNNING,
        )

        try:
            self._clear_osm_data()
            self.log(
                "Импорт дорожного и пешеходного графов, зданий "
                "и объектов инфраструктуры..."
            )

            processor = (
                osmium.FileProcessor(str(REGION_PBF))
                .with_locations("flex_mem")
                .with_areas()
            )

            for obj in processor:
                self.objects_seen += 1
                if self.objects_seen % 100_000 == 0:
                    self.log(
                        f"Обработано OSM-объектов: {self.objects_seen:,}; "
                        f"рёбер графа: {self.edges_buffered:,}; "
                        f"зданий: {self.buildings_buffered:,}; "
                        f"инфраструктуры: {self.social_buffered:,}"
                    )

                tags = _tags_dict(obj.tags)

                if obj.is_node():
                    self._buffer_social_node(obj, tags)
                elif obj.is_way():
                    self._buffer_graph_way(obj, tags)
                    self._buffer_linear_stop(obj, tags)
                elif obj.is_area():
                    self._buffer_area(obj, tags)

            self._flush_graph()
            self._flush_buildings()
            self._flush_social()

            nodes_count = RoadNode.objects.count()
            edges_count = RoadEdge.objects.count()
            walk_edges_count = RoadEdge.objects.filter(walkable=True).count()
            drive_edges_count = RoadEdge.objects.filter(drivable=True).count()
            buildings_count = OsmBuilding.objects.count()
            social_objects_count = SocialObject.objects.filter(source="osm").count()

            self.import_run.status = OsmImportRun.Status.COMPLETED
            self.import_run.finished_at = timezone.now()
            self.import_run.nodes_count = nodes_count
            self.import_run.edges_count = edges_count
            self.import_run.walk_edges_count = walk_edges_count
            self.import_run.drive_edges_count = drive_edges_count
            self.import_run.buildings_count = buildings_count
            self.import_run.social_objects_count = social_objects_count
            self.import_run.save(
                update_fields=[
                    "status",
                    "finished_at",
                    "nodes_count",
                    "edges_count",
                    "walk_edges_count",
                    "drive_edges_count",
                    "buildings_count",
                    "social_objects_count",
                ]
            )

            return self.import_run

        except Exception as exc:
            self.import_run.status = OsmImportRun.Status.FAILED
            self.import_run.finished_at = timezone.now()
            self.import_run.error_message = str(exc)
            self.import_run.save(
                update_fields=["status", "finished_at", "error_message"]
            )
            raise
