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
        STOP = "stop", "Остановка"
        SPORT = "sport", "Спортивный объект"
        PHARMACY = "pharmacy", "Аптека"
        CULTURE = "culture", "Объект культуры"
        OTHER = "other", "Другое"

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=32, choices=Category.choices)
    subcategory = models.CharField(max_length=128, blank=True)
    address = models.CharField(max_length=500, blank=True)
    geometry = models.PointField(srid=4326)
    capacity = models.FloatField(null=True, blank=True)
    capacity_unit = models.CharField(max_length=64, blank=True)
    source = models.CharField(max_length=255, blank=True)
    source_id = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "name"]

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
