from django.db import migrations, models
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialobject",
            name="footprint",
            field=django.contrib.gis.db.models.fields.PolygonField(blank=True, null=True, srid=4326),
        ),
        migrations.AddIndex(
            model_name="socialobject",
            index=models.Index(fields=["category", "is_active"], name="core_social_categor_a83fa5_idx"),
        ),
        migrations.AddIndex(
            model_name="socialobject",
            index=models.Index(fields=["source", "source_id"], name="core_social_source_35a47d_idx"),
        ),
        migrations.CreateModel(
            name="RoadNode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("osm_id", models.BigIntegerField(db_index=True, unique=True)),
                ("geometry", django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name="RoadEdge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("osm_way_id", models.BigIntegerField(db_index=True)),
                ("segment_index", models.PositiveIntegerField()),
                ("source_osm_id", models.BigIntegerField(db_index=True)),
                ("target_osm_id", models.BigIntegerField(db_index=True)),
                ("geometry", django.contrib.gis.db.models.fields.LineStringField(srid=4326)),
                ("length_m", models.FloatField()),
                ("highway", models.CharField(blank=True, max_length=64)),
                ("name", models.CharField(blank=True, max_length=255)),
                ("oneway", models.BooleanField(default=False)),
                ("walkable", models.BooleanField(db_index=True, default=True)),
            ],
        ),
        migrations.AddIndex(
            model_name="roadedge",
            index=models.Index(fields=["source_osm_id", "target_osm_id"], name="core_roaded_source__9510a9_idx"),
        ),
        migrations.AddIndex(
            model_name="roadedge",
            index=models.Index(fields=["walkable", "highway"], name="core_roaded_walkabl_02031e_idx"),
        ),
        migrations.AddConstraint(
            model_name="roadedge",
            constraint=models.UniqueConstraint(
                fields=("osm_way_id", "segment_index", "source_osm_id", "target_osm_id"),
                name="unique_osm_road_segment",
            ),
        ),
    ]
