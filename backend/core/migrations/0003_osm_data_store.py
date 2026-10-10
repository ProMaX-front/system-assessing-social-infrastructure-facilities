from django.db import migrations, models
import django.contrib.gis.db.models.fields
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_osm_graph_and_footprints"),
    ]

    operations = [
        migrations.CreateModel(
            name="OsmImportRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("region_name", models.CharField(default="Тюменская область", max_length=255)),
                ("source_url", models.URLField(max_length=1000)),
                ("source_file", models.CharField(blank=True, max_length=1000)),
                ("source_timestamp", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("running", "Выполняется"), ("completed", "Завершён"), ("failed", "Ошибка")], db_index=True, default="running", max_length=16)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("nodes_count", models.PositiveBigIntegerField(default=0)),
                ("edges_count", models.PositiveBigIntegerField(default=0)),
                ("walk_edges_count", models.PositiveBigIntegerField(default=0)),
                ("drive_edges_count", models.PositiveBigIntegerField(default=0)),
                ("buildings_count", models.PositiveBigIntegerField(default=0)),
                ("social_objects_count", models.PositiveBigIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),
        migrations.AlterField(
            model_name="socialobject",
            name="category",
            field=models.CharField(
                choices=[
                    ("school", "Школа"),
                    ("kindergarten", "Детский сад"),
                    ("college", "Колледж / техникум"),
                    ("university", "Высшее учебное заведение"),
                    ("polyclinic", "Поликлиника / амбулатория"),
                    ("hospital", "Больница"),
                    ("pharmacy", "Аптека"),
                    ("shop", "Магазин"),
                    ("stop", "Остановка общественного транспорта"),
                    ("sport", "Спортивный объект"),
                    ("culture", "Объект культуры"),
                    ("social", "Объект социального обслуживания"),
                    ("other", "Прочий социальный объект"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="socialobject",
            name="footprint",
            field=django.contrib.gis.db.models.fields.GeometryField(
                blank=True,
                null=True,
                srid=4326,
            ),
        ),
        migrations.AlterField(
            model_name="socialobject",
            name="source",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="socialobject",
            name="source_id",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="socialobject",
            name="osm_type",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="socialobject",
            name="osm_id",
            field=models.BigIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="socialobject",
            name="osm_tags",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="socialobject",
            name="import_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="social_objects",
                to="core.osmimportrun",
            ),
        ),
        migrations.AddField(
            model_name="socialobject",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                default=django.utils.timezone.now,
            ),
            preserve_default=False,
        ),
        migrations.AddIndex(
            model_name="socialobject",
            index=models.Index(fields=["osm_type", "osm_id"], name="social_osm_type_id_idx"),
        ),
        migrations.AlterField(
            model_name="normative",
            name="category",
            field=models.CharField(
                choices=[
                    ("school", "Школа"),
                    ("kindergarten", "Детский сад"),
                    ("college", "Колледж / техникум"),
                    ("university", "Высшее учебное заведение"),
                    ("polyclinic", "Поликлиника / амбулатория"),
                    ("hospital", "Больница"),
                    ("pharmacy", "Аптека"),
                    ("shop", "Магазин"),
                    ("stop", "Остановка общественного транспорта"),
                    ("sport", "Спортивный объект"),
                    ("culture", "Объект культуры"),
                    ("social", "Объект социального обслуживания"),
                    ("other", "Прочий социальный объект"),
                ],
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="roadnode",
            name="walkable",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="roadnode",
            name="drivable",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="roadnode",
            name="import_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="graph_nodes",
                to="core.osmimportrun",
            ),
        ),
        migrations.AlterField(
            model_name="roadedge",
            name="highway",
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AlterField(
            model_name="roadedge",
            name="walkable",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="drivable",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="surface",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="access",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="foot",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="motor_vehicle",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="walk_forward",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="walk_backward",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="drive_forward",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="drive_backward",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="bridge",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="tunnel",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="roadedge",
            name="import_run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="graph_edges",
                to="core.osmimportrun",
            ),
        ),
        migrations.AddIndex(
            model_name="roadedge",
            index=models.Index(fields=["drivable", "highway"], name="road_drive_highway_idx"),
        ),
        migrations.CreateModel(
            name="OsmBuilding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("osm_type", models.CharField(max_length=16)),
                ("osm_id", models.BigIntegerField()),
                ("name", models.CharField(blank=True, max_length=255)),
                ("address", models.CharField(blank=True, max_length=500)),
                ("building_type", models.CharField(blank=True, db_index=True, max_length=128)),
                ("infrastructure_category", models.CharField(
                    blank=True,
                    choices=[
                        ("school", "Школа"),
                        ("kindergarten", "Детский сад"),
                        ("college", "Колледж / техникум"),
                        ("university", "Высшее учебное заведение"),
                        ("polyclinic", "Поликлиника / амбулатория"),
                        ("hospital", "Больница"),
                        ("pharmacy", "Аптека"),
                        ("shop", "Магазин"),
                        ("stop", "Остановка общественного транспорта"),
                        ("sport", "Спортивный объект"),
                        ("culture", "Объект культуры"),
                        ("social", "Объект социального обслуживания"),
                        ("other", "Прочий социальный объект"),
                    ],
                    db_index=True,
                    default="",
                    max_length=32,
                )),
                ("geometry", django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
                ("centroid", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("osm_tags", models.JSONField(blank=True, default=dict)),
                ("imported_at", models.DateTimeField(auto_now_add=True)),
                ("import_run", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="buildings",
                    to="core.osmimportrun",
                )),
            ],
            options={
                "ordering": ["osm_type", "osm_id"],
            },
        ),
        migrations.AddConstraint(
            model_name="osmbuilding",
            constraint=models.UniqueConstraint(
                fields=("osm_type", "osm_id"),
                name="unique_osm_building",
            ),
        ),
        migrations.AddIndex(
            model_name="osmbuilding",
            index=models.Index(
                fields=["infrastructure_category", "building_type"],
                name="building_cat_type_idx",
            ),
        ),
    ]
