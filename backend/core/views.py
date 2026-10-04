from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdministrativeUnit, SocialObject, Normative
from .serializers import (
    AdministrativeUnitSerializer,
    NormativeSerializer,
    RegisterSerializer,
    SocialObjectSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


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
        return qs[:5000]


class NormativeListView(generics.ListAPIView):
    serializer_class = NormativeSerializer

    def get_queryset(self):
        qs = Normative.objects.all()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class NearestAnalysisView(APIView):
    def post(self, request):
        try:
            lat = float(request.data["latitude"])
            lon = float(request.data["longitude"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {"detail": "Передайте корректные latitude и longitude."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        point = Point(lon, lat, srid=4326)
        requested_categories = request.data.get("categories") or [value for value, _ in SocialObject.Category.choices]
        results = []

        for category in requested_categories:
            nearest = (
                SocialObject.objects.filter(category=category, is_active=True)
                .annotate(distance=Distance("geometry", point))
                .order_by("distance")
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
                    "object": None,
                    "distance_m": None,
                    "normative_distance_m": normative.max_distance_m if normative else None,
                    "compliant": None,
                    "message": "Объекты данной категории не найдены.",
                })
                continue

            distance_m = round(nearest.distance.m, 1)
            limit = normative.max_distance_m if normative else None
            results.append({
                "category": category,
                "object": SocialObjectSerializer(nearest).data,
                "distance_m": distance_m,
                "normative_distance_m": limit,
                "compliant": (distance_m <= limit) if limit is not None else None,
                "normative": NormativeSerializer(normative).data if normative else None,
            })

        return Response({
            "point": {"latitude": lat, "longitude": lon},
            "calculation_method": "geodesic_distance_mvp",
            "results": results,
        })
