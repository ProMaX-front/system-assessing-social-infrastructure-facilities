from django.contrib import admin
from .models import AdministrativeUnit, SocialObject, Normative

@admin.register(AdministrativeUnit)
class AdministrativeUnitAdmin(admin.ModelAdmin):
    list_display = ("name", "unit_type", "parent", "population")
    list_filter = ("unit_type",)
    search_fields = ("name", "oktmo", "okato")

@admin.register(SocialObject)
class SocialObjectAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "address", "capacity", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "address")

@admin.register(Normative)
class NormativeAdmin(admin.ModelAdmin):
    list_display = ("category", "max_distance_m", "movement_mode", "territory", "priority")
    list_filter = ("category", "movement_mode")
