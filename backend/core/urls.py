from django.urls import path
from .views import (
    AdministrativeUnitListView,
    MeView,
    NearestAnalysisView,
    NormativeListView,
    RegisterView,
    SocialObjectListView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("territories/", AdministrativeUnitListView.as_view()),
    path("social-objects/", SocialObjectListView.as_view()),
    path("normatives/", NormativeListView.as_view()),
    path("analysis/nearest/", NearestAnalysisView.as_view()),
]
