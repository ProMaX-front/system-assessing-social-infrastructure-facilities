import json
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point, Polygon
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdministrativeUnit, Normative, OsmBuilding, SocialObject
from .routing import calculate_pedestrian_route
from .serializers import (
    AdministrativeUnitSerializer,
    NormativeSerializer,
    SocialObjectSerializer,
    UserSerializer,
)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class AdministrativeUnitListView(generics.ListAPIView):
    serializer_class = AdministrativeUnitSerializer

    def get_queryset(self):
        qs = AdministrativeUnit.objects.all()
        unit_type = self.request.query_params.get("type")
        parent = self.request.query_params.get("parent")
        if unit_type:
            qs = qs.filter(unit_type=unit_type)
        if parent:
            qs = qs.filter(parent_id=parent)
        return qs


class SocialObjectListView(generics.ListAPIView):
    serializer_class = SocialObjectSerializer

    def get_queryset(self):
        qs = SocialObject.objects.filter(is_active=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs[:10000]


class NormativeListView(generics.ListAPIView):
    serializer_class = NormativeSerializer

    def get_queryset(self):
        qs = Normative.objects.all()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class MapLayersView(APIView):
    """
    Возвращает только геоданные, попадающие в текущую область карты.

    На обзорных масштабах передаются здания, уже связанные с социальной
    инфраструктурой. При приближении до zoom >= 14 можно отображать все
    импортированные здания OSM в видимой области.
    """

    SOCIAL_LIMIT = 5000
    BUILDING_LIMIT = 5000

    def get(self, request):
        bbox_value = request.query_params.get("bbox", "")
        try:
            min_lon, min_lat, max_lon, max_lat = [
                float(value) for value in bbox_value.split(",")
            ]
        except (TypeError, ValueError):
            return Response(
                {
                    "detail": (
                        "Передайте bbox в формате "
                        "min_lon,min_lat,max_lon,max_lat."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if min_lon >= max_lon or min_lat >= max_lat:
            return Response(
                {"detail": "Некорректные границы области карты."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            zoom = float(request.query_params.get("zoom", 12))
        except (TypeError, ValueError):
            zoom = 12

        bbox = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
        bbox.srid = 4326

        category_values = request.query_params.get("categories", "")
        categories = [
            value.strip()
            for value in category_values.split(",")
            if value.strip()
        ]
        valid_categories = {
            value for value, _ in SocialObject.Category.choices
        }
        categories = [
            category for category in categories
            if category in valid_categories
        ]

        social_qs = SocialObject.objects.filter(
            is_active=True,
            geometry__intersects=bbox,
        )
        if categories:
            social_qs = social_qs.filter(category__in=categories)

        social_rows = list(
            social_qs.only(
                "id",
                "name",
                "category",
                "subcategory",
                "address",
                "geometry",
                "source_id",
            )[: self.SOCIAL_LIMIT + 1]
        )
        social_truncated = len(social_rows) > self.SOCIAL_LIMIT
        social_rows = social_rows[: self.SOCIAL_LIMIT]

        social_features = [
            {
                "type": "Feature",
                "id": obj.id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [obj.geometry.x, obj.geometry.y],
                },
                "properties": {
                    "id": obj.id,
                    "name": obj.name,
                    "category": obj.category,
                    "category_label": obj.get_category_display(),
                    "subcategory": obj.subcategory,
                    "address": obj.address,
                    "source_id": obj.source_id,
                },
            }
            for obj in social_rows
        ]

        building_qs = OsmBuilding.objects.filter(
            geometry__intersects=bbox,
        )
        if categories:
            building_qs = building_qs.filter(
                infrastructure_category__in=categories
            )
        elif zoom < 14:
            building_qs = building_qs.exclude(
                infrastructure_category=""
            )

        building_rows = list(
            building_qs.only(
                "id",
                "osm_type",
                "osm_id",
                "name",
                "address",
                "building_type",
                "infrastructure_category",
                "geometry",
            )[: self.BUILDING_LIMIT + 1]
        )
        buildings_truncated = len(building_rows) > self.BUILDING_LIMIT
        building_rows = building_rows[: self.BUILDING_LIMIT]

        building_features = [
            {
                "type": "Feature",
                "id": building.id,
                "geometry": json.loads(building.geometry.geojson),
                "properties": {
                    "id": building.id,
                    "osm_type": building.osm_type,
                    "osm_id": building.osm_id,
                    "name": building.name,
                    "address": building.address,
                    "building_type": building.building_type,
                    "category": building.infrastructure_category,
                    "category_label": (
                        dict(SocialObject.Category.choices).get(
                            building.infrastructure_category,
                            "",
                        )
                    ),
                },
            }
            for building in building_rows
        ]

        return Response(
            {
                "social_objects": {
                    "type": "FeatureCollection",
                    "features": social_features,
                },
                "buildings": {
                    "type": "FeatureCollection",
                    "features": building_features,
                },
                "meta": {
                    "zoom": zoom,
                    "social_objects_count": len(social_features),
                    "buildings_count": len(building_features),
                    "social_objects_truncated": social_truncated,
                    "buildings_truncated": buildings_truncated,
                    "all_buildings_visible": zoom >= 14 and not categories,
                },
            }
        )


def _analysis_geometry_for_object(obj):
    """
    Возвращает наиболее полную реальную геометрию объекта для подсветки
    результата анализа: собственный контур OSM, связанное здание либо
    здание, пространственно содержащее точечный объект.
    """
    if obj.footprint:
        return json.loads(obj.footprint.geojson)

    building = None

    if obj.osm_type and obj.osm_id:
        building = OsmBuilding.objects.filter(
            osm_type=obj.osm_type,
            osm_id=obj.osm_id,
        ).only("geometry").first()

    if building is None:
        building = (
            OsmBuilding.objects.filter(
                infrastructure_category=obj.category,
                geometry__covers=obj.geometry,
            )
            .only("geometry")
            .first()
        )

    if building is None:
        building = (
            OsmBuilding.objects.filter(
                geometry__covers=obj.geometry,
            )
            .only("geometry")
            .first()
        )

    if building:
        return json.loads(building.geometry.geojson)

    return None


class NearestAnalysisView(APIView):
    def post(self, request):
        try:
            lat = float(request.data["latitude"])
            lon = float(request.data["longitude"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {"detail": "Передайте корректные широту и долготу."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        point = Point(lon, lat, srid=4326)
        category_labels = dict(SocialObject.Category.choices)
        requested_categories = request.data.get("categories") or [
            value for value, _ in SocialObject.Category.choices
        ]
        results = []

        for category in requested_categories:
            category_label = category_labels.get(category, category)
            nearest = (
                SocialObject.objects.filter(category=category, is_active=True)
                .annotate(direct_distance=Distance("geometry", point))
                .order_by("direct_distance")
                .first()
            )
            normative = (
                Normative.objects.filter(category=category, max_distance_m__isnull=False)
                .order_by("priority", "-valid_from")
                .first()
            )

            if nearest is None:
                results.append({
                    "category": category,
                    "category_label": category_label,
                    "object": None,
                    "distance_m": None,
                    "direct_distance_m": None,
                    "normative_distance_m": normative.max_distance_m if normative else None,
                    "compliant": None,
                    "route_geometry": None,
                    "route_is_osm": False,
                    "distance_method": "Объект отсутствует",
                    "message": "Объекты данной категории не найдены.",
                })
                continue

            direct_distance_m = round(nearest.direct_distance.m, 1)
            route = calculate_pedestrian_route(point, nearest.geometry)

            if route:
                distance_m = route["distance_m"]
                route_geometry = route["geometry"]
                route_is_osm = True
                distance_method = "По пешеходному графу OpenStreetMap"
            else:
                distance_m = direct_distance_m
                route_geometry = {
                    "type": "LineString",
                    "coordinates": [
                        [lon, lat],
                        [nearest.geometry.x, nearest.geometry.y],
                    ],
                }
                route_is_osm = False
                distance_method = "По прямой — дорожный граф OSM ещё не импортирован"

            limit = normative.max_distance_m if normative else None
            object_data = SocialObjectSerializer(nearest).data
            analysis_geometry = _analysis_geometry_for_object(nearest)
            if analysis_geometry is not None:
                object_data["footprint"] = analysis_geometry

            results.append({
                "category": category,
                "category_label": category_label,
                "object": object_data,
                "distance_m": distance_m,
                "direct_distance_m": direct_distance_m,
                "normative_distance_m": limit,
                "compliant": (distance_m <= limit) if limit is not None else None,
                "route_geometry": route_geometry,
                "route_is_osm": route_is_osm,
                "distance_method": distance_method,
                "normative": NormativeSerializer(normative).data if normative else None,
            })

        return Response({
            "point": {"latitude": lat, "longitude": lon},
            "calculation_method": (
                "pedestrian_osm_graph_with_direct_fallback"
            ),
            "results": results,
        })
