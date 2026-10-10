from django.urls import path

from .views import (
    AdministrativeUnitListView,
    MapLayersView,
    MeView,
    NearestAnalysisView,
    NormativeListView,
    SocialObjectListView,
)

urlpatterns = [
    path("auth/me/", MeView.as_view()),
    path("territories/", AdministrativeUnitListView.as_view()),
    path("social-objects/", SocialObjectListView.as_view()),
    path("map/layers/", MapLayersView.as_view()),
    path("normatives/", NormativeListView.as_view()),
    path("analysis/nearest/", NearestAnalysisView.as_view()),
]
