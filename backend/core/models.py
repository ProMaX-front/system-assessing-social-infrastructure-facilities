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
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    oktmo = models.CharField(max_length=20, blank=True)
    okato = models.CharField(max_length=20, blank=True)
    population = models.PositiveIntegerField(null=True, blank=True)
    geometry = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SocialObject(models.Model):
    class Category(models.TextChoices):
        SCHOOL = "school", "Школа"
        KINDERGARTEN = "kindergarten", "Детский сад"
        POLYCLINIC = "polyclinic", "Поликлиника"
        HOSPITAL = "hospital", "Больница"
        SHOP = "shop", "Магазин"
        STOP = "stop", "Остановка общественного транспорта"
        SPORT = "sport", "Спортивный объект"
        PHARMACY = "pharmacy", "Аптека"
        CULTURE = "culture", "Объект культуры"
        OTHER = "other", "Прочий социальный объект"

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=Category.choices)
    subcategory = models.CharField(max_length=128, blank=True)
    address = models.CharField(max_length=500, blank=True)
    geometry = models.PointField(srid=4326)
    footprint = models.PolygonField(srid=4326, null=True, blank=True)
    capacity = models.FloatField(null=True, blank=True)
    capacity_unit = models.CharField(max_length=64, blank=True)
    source = models.CharField(max_length=255, blank=True)
    source_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["source", "source_id"]),
        ]

    def __str__(self):
        return self.name


class Normative(models.Model):
    category = models.CharField(max_length=32, choices=SocialObject.Category.choices)
    territory = models.ForeignKey(AdministrativeUnit, null=True, blank=True, on_delete=models.CASCADE, related_name="normatives")
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
    osm_id = models.BigIntegerField(unique=True, db_index=True)
    geometry = models.PointField(srid=4326)

    def __str__(self):
        return f"OSM node {self.osm_id}"


class RoadEdge(models.Model):
    osm_way_id = models.BigIntegerField(db_index=True)
    segment_index = models.PositiveIntegerField()
    source_osm_id = models.BigIntegerField(db_index=True)
    target_osm_id = models.BigIntegerField(db_index=True)
    geometry = models.LineStringField(srid=4326)
    length_m = models.FloatField()
    highway = models.CharField(max_length=64, blank=True)
    name = models.CharField(max_length=255, blank=True)
    oneway = models.BooleanField(default=False)
    walkable = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["source_osm_id", "target_osm_id"]),
            models.Index(fields=["walkable", "highway"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["osm_way_id", "segment_index", "source_osm_id", "target_osm_id"],
                name="unique_osm_road_segment",
            )
        ]

    def __str__(self):
        return f"OSM way {self.osm_way_id}: {self.source_osm_id} → {self.target_osm_id}"
