from django.contrib import admin

from .models import (
    AdministrativeUnit,
    Normative,
    OsmBuilding,
    OsmImportRun,
    RoadEdge,
    RoadNode,
    SocialObject,
)


@admin.register(AdministrativeUnit)
class AdministrativeUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "unit_type", "parent", "population")
    list_filter = ("unit_type",)
    search_fields = ("name", "oktmo", "okato")


@admin.register(SocialObject)
class SocialObjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "address",
        "source",
        "osm_type",
        "osm_id",
        "is_active",
    )
    list_filter = ("category", "source", "is_active")
    search_fields = ("name", "address", "source_id")


@admin.register(OsmBuilding)
class OsmBuildingAdmin(admin.ModelAdmin):
    list_display = (
        "osm_type",
        "osm_id",
        "name",
        "building_type",
        "infrastructure_category",
    )
    list_filter = ("infrastructure_category", "building_type")
    search_fields = ("name", "address", "osm_id")


@admin.register(OsmImportRun)
class OsmImportRunAdmin(admin.ModelAdmin):
    list_display = (
        "region_name",
        "status",
        "started_at",
        "finished_at",
        "nodes_count",
        "edges_count",
        "buildings_count",
        "social_objects_count",
    )
    list_filter = ("status", "region_name")
    readonly_fields = (
        "started_at",
        "finished_at",
        "nodes_count",
        "edges_count",
        "walk_edges_count",
        "drive_edges_count",
        "buildings_count",
        "social_objects_count",
        "error_message",
    )


@admin.register(RoadNode)
class RoadNodeAdmin(admin.ModelAdmin):
    list_display = ("osm_id", "walkable", "drivable", "import_run")
    list_filter = ("walkable", "drivable")
    search_fields = ("osm_id",)


@admin.register(RoadEdge)
class RoadEdgeAdmin(admin.ModelAdmin):
    list_display = (
        "osm_way_id",
        "segment_index",
        "highway",
        "name",
        "length_m",
        "walkable",
        "drivable",
    )
    list_filter = ("highway", "walkable", "drivable", "bridge", "tunnel")
    search_fields = ("osm_way_id", "name")


@admin.register(Normative)
class NormativeAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "max_distance_m",
        "movement_mode",
        "territory",
        "priority",
    )
    list_filter = ("category", "movement_mode")
