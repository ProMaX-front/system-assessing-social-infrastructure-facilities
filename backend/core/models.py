from django.contrib.gis.db import models


class AdministrativeUnit(models.Model):
    class UnitType(models.TextChoices):
        COUNTRY = "country", "Страна"
        REGION = "region", "Субъект РФ"
        MUNICIPALITY = "municipality", "Муниципальное образование"
        SETTLEMENT = "settlement", "Населённый пункт"
        DISTRICT = "district", "Район"
        MICRODISTRICT = "microdistrict", "Микрорайон"
        QUARTER = "quarter", "Квартал"

    name = models.CharField(max_length=255)
    unit_type = models.CharField(max_length=32, choices=UnitType.choices)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    oktmo = models.CharField(max_length=20, blank=True)
    okato = models.CharField(max_length=20, blank=True)
    population = models.PositiveIntegerField(null=True, blank=True)
    geometry = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OsmImportRun(models.Model):
    class Status(models.TextChoices):
        RUNNING = "running", "Выполняется"
        COMPLETED = "completed", "Завершён"
        FAILED = "failed", "Ошибка"

    region_name = models.CharField(max_length=255, default="Тюменская область")
    source_url = models.URLField(max_length=1000)
    source_file = models.CharField(max_length=1000, blank=True)
    source_timestamp = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.RUNNING,
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    nodes_count = models.PositiveBigIntegerField(default=0)
    edges_count = models.PositiveBigIntegerField(default=0)
    walk_edges_count = models.PositiveBigIntegerField(default=0)
    drive_edges_count = models.PositiveBigIntegerField(default=0)
    buildings_count = models.PositiveBigIntegerField(default=0)
    social_objects_count = models.PositiveBigIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.region_name} — {self.get_status_display()} — {self.started_at:%d.%m.%Y %H:%M}"


class SocialObject(models.Model):
    class Category(models.TextChoices):
        SCHOOL = "school", "Школа"
        KINDERGARTEN = "kindergarten", "Детский сад"
        COLLEGE = "college", "Колледж / техникум"
        UNIVERSITY = "university", "Высшее учебное заведение"
        POLYCLINIC = "polyclinic", "Поликлиника / амбулатория"
        HOSPITAL = "hospital", "Больница"
        PHARMACY = "pharmacy", "Аптека"
        SHOP = "shop", "Магазин"
        STOP = "stop", "Остановка общественного транспорта"
        SPORT = "sport", "Спортивный объект"
        CULTURE = "culture", "Объект культуры"
        SOCIAL = "social", "Объект социального обслуживания"
        OTHER = "other", "Прочий социальный объект"

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=Category.choices)
    subcategory = models.CharField(max_length=128, blank=True)
    address = models.CharField(max_length=500, blank=True)

    # Точка, используемая как представитель объекта при поиске ближайшего объекта.
    geometry = models.PointField(srid=4326)

    # Полная геометрия объекта из OSM: Polygon или MultiPolygon.
    footprint = models.GeometryField(srid=4326, null=True, blank=True)

    capacity = models.FloatField(null=True, blank=True)
    capacity_unit = models.CharField(max_length=64, blank=True)

    source = models.CharField(max_length=255, blank=True, db_index=True)
    source_id = models.CharField(max_length=255, blank=True, db_index=True)
    osm_type = models.CharField(max_length=16, blank=True)
    osm_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    import_run = models.ForeignKey(
        OsmImportRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="social_objects",
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(
                fields=["category", "is_active"],
                name="core_social_categor_a83fa5_idx",
            ),
            models.Index(
                fields=["source", "source_id"],
                name="core_social_source_35a47d_idx",
            ),
            models.Index(
                fields=["osm_type", "osm_id"],
                name="social_osm_type_id_idx",
            ),
        ]

    def __str__(self):
        return self.name


class OsmBuilding(models.Model):
    """
    Полный реестр геометрий зданий из OSM в исследуемой территории.
    Категория заполняется, если назначение здания можно определить по тегам OSM.
    """

    osm_type = models.CharField(max_length=16)
    osm_id = models.BigIntegerField()
    name = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=500, blank=True)
    building_type = models.CharField(max_length=128, blank=True, db_index=True)
    infrastructure_category = models.CharField(
        max_length=32,
        choices=SocialObject.Category.choices,
        blank=True,
        default="",
        db_index=True,
    )
    geometry = models.MultiPolygonField(srid=4326)
    centroid = models.PointField(srid=4326)
    osm_tags = models.JSONField(default=dict, blank=True)
    import_run = models.ForeignKey(
        OsmImportRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="buildings",
    )
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["osm_type", "osm_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["osm_type", "osm_id"],
                name="unique_osm_building",
            )
        ]
        indexes = [
            models.Index(
                fields=["infrastructure_category", "building_type"],
                name="building_cat_type_idx",
            ),
        ]

    def __str__(self):
        label = self.name or self.building_type or "Здание"
        return f"{label} ({self.osm_type}/{self.osm_id})"


class Normative(models.Model):
    category = models.CharField(max_length=32, choices=SocialObject.Category.choices)
    territory = models.ForeignKey(
        AdministrativeUnit,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="normatives",
    )
    settlement_type = models.CharField(max_length=64, blank=True)
    building_type = models.CharField(max_length=64, blank=True)
    max_distance_m = models.PositiveIntegerField(null=True, blank=True)
    max_time_min = models.PositiveIntegerField(null=True, blank=True)
    movement_mode = models.CharField(max_length=32, default="walking")
    min_supply_value = models.FloatField(null=True, blank=True)
    min_supply_unit = models.CharField(max_length=64, blank=True)
    legal_document = models.CharField(max_length=500)
    legal_clause = models.CharField(max_length=128, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ["category", "priority"]

    def __str__(self):
        return f"{self.get_category_display()} — {self.legal_document}"


class RoadNode(models.Model):
    """
    Общие вершины транспортного графа. Один узел может одновременно
    принадлежать автомобильному и пешеходному графу.
    """

    osm_id = models.BigIntegerField(unique=True, db_index=True)
    geometry = models.PointField(srid=4326)
    walkable = models.BooleanField(default=False, db_index=True)
    drivable = models.BooleanField(default=False, db_index=True)
    import_run = models.ForeignKey(
        OsmImportRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="graph_nodes",
    )

    def __str__(self):
        return f"OSM node {self.osm_id}"


class RoadEdge(models.Model):
    """
    Унифицированное ребро графа OSM.
    Пешеходный граф = walkable=True.
    Автомобильный граф = drivable=True.
    Такой подход не дублирует одну и ту же геометрию дороги в двух таблицах.
    """

    osm_way_id = models.BigIntegerField(db_index=True)
    segment_index = models.PositiveIntegerField()
    source_osm_id = models.BigIntegerField(db_index=True)
    target_osm_id = models.BigIntegerField(db_index=True)
    geometry = models.LineStringField(srid=4326)
    length_m = models.FloatField()

    highway = models.CharField(max_length=64, blank=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    surface = models.CharField(max_length=64, blank=True)
    access = models.CharField(max_length=64, blank=True)
    foot = models.CharField(max_length=64, blank=True)
    motor_vehicle = models.CharField(max_length=64, blank=True)

    oneway = models.BooleanField(default=False)
    walkable = models.BooleanField(default=False, db_index=True)
    drivable = models.BooleanField(default=False, db_index=True)

    walk_forward = models.BooleanField(default=True)
    walk_backward = models.BooleanField(default=True)
    drive_forward = models.BooleanField(default=True)
    drive_backward = models.BooleanField(default=True)

    bridge = models.BooleanField(default=False)
    tunnel = models.BooleanField(default=False)
    osm_tags = models.JSONField(default=dict, blank=True)

    import_run = models.ForeignKey(
        OsmImportRun,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="graph_edges",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["source_osm_id", "target_osm_id"],
                name="core_roaded_source__9510a9_idx",
            ),
            models.Index(
                fields=["walkable", "highway"],
                name="core_roaded_walkabl_02031e_idx",
            ),
            models.Index(
                fields=["drivable", "highway"],
                name="road_drive_highway_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "osm_way_id",
                    "segment_index",
                    "source_osm_id",
                    "target_osm_id",
                ],
                name="unique_osm_road_segment",
            )
        ]

    def __str__(self):
        return (
            f"OSM way {self.osm_way_id}: "
            f"{self.source_osm_id} → {self.target_osm_id}"
        )
