from django.contrib.auth.models import User
from rest_framework import serializers
from .models import AdministrativeUnit, SocialObject, Normative


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


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
        return obj.geometry.geojson if obj.geometry else None


class SocialObjectSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    longitude = serializers.FloatField(source="geometry.x", read_only=True)
    latitude = serializers.FloatField(source="geometry.y", read_only=True)

    class Meta:
        model = SocialObject
        fields = (
            "id", "name", "category", "category_label", "subcategory", "address",
            "longitude", "latitude", "capacity", "capacity_unit", "source", "is_active"
        )


class NormativeSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Normative
        fields = "__all__"
