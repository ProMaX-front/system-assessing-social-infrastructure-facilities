import json

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import AdministrativeUnit, Normative, SocialObject


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_staff")


class AdministrativeUnitSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = AdministrativeUnit
        fields = ("id", "name", "unit_type", "parent_id", "oktmo", "okato", "population", "geometry")

    def get_geometry(self, obj):
        return json.loads(obj.geometry.geojson) if obj.geometry else None


class SocialObjectSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    longitude = serializers.FloatField(source="geometry.x", read_only=True)
    latitude = serializers.FloatField(source="geometry.y", read_only=True)
    footprint = serializers.SerializerMethodField()

    class Meta:
        model = SocialObject
        fields = (
            "id", "name", "category", "category_label", "subcategory", "address",
            "longitude", "latitude", "footprint", "capacity", "capacity_unit",
            "source", "source_id", "is_active",
        )

    def get_footprint(self, obj):
        return json.loads(obj.footprint.geojson) if obj.footprint else None


class NormativeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Normative
        fields = "__all__"
