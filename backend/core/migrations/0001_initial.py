from django.db import migrations, models
import django.contrib.gis.db.models.fields
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AdministrativeUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("unit_type", models.CharField(choices=[("country", "Страна"), ("region", "Субъект РФ"), ("municipality", "Муниципальное образование"), ("settlement", "Населённый пункт"), ("district", "Район"), ("microdistrict", "Микрорайон"), ("quarter", "Квартал")], max_length=32)),
                ("oktmo", models.CharField(blank=True, max_length=20)),
                ("okato", models.CharField(blank=True, max_length=20)),
                ("population", models.PositiveIntegerField(blank=True, null=True)),
                ("geometry", django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="core.administrativeunit")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SocialObject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("category", models.CharField(choices=[("school", "Школа"), ("kindergarten", "Детский сад"), ("polyclinic", "Поликлиника"), ("hospital", "Больница"), ("shop", "Магазин"), ("stop", "Остановка"), ("sport", "Спортивный объект"), ("pharmacy", "Аптека"), ("culture", "Объект культуры"), ("other", "Другое")], max_length=32)),
                ("subcategory", models.CharField(blank=True, max_length=128)),
                ("address", models.CharField(blank=True, max_length=500)),
                ("geometry", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("capacity", models.FloatField(blank=True, null=True)),
                ("capacity_unit", models.CharField(blank=True, max_length=64)),
                ("source", models.CharField(blank=True, max_length=255)),
                ("source_id", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["category", "name"]},
        ),
        migrations.CreateModel(
            name="Normative",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("category", models.CharField(choices=[("school", "Школа"), ("kindergarten", "Детский сад"), ("polyclinic", "Поликлиника"), ("hospital", "Больница"), ("shop", "Магазин"), ("stop", "Остановка"), ("sport", "Спортивный объект"), ("pharmacy", "Аптека"), ("culture", "Объект культуры"), ("other", "Другое")], max_length=32)),
                ("settlement_type", models.CharField(blank=True, max_length=64)),
                ("building_type", models.CharField(blank=True, max_length=64)),
                ("max_distance_m", models.PositiveIntegerField(blank=True, null=True)),
                ("max_time_min", models.PositiveIntegerField(blank=True, null=True)),
                ("movement_mode", models.CharField(default="walking", max_length=32)),
                ("min_supply_value", models.FloatField(blank=True, null=True)),
                ("min_supply_unit", models.CharField(blank=True, max_length=64)),
                ("legal_document", models.CharField(max_length=500)),
                ("legal_clause", models.CharField(blank=True, max_length=128)),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_to", models.DateField(blank=True, null=True)),
                ("priority", models.PositiveIntegerField(default=100)),
                ("territory", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="normatives", to="core.administrativeunit")),
            ],
            options={"ordering": ["category", "priority"]},
        ),
    ]
