from django.urls import include, path


urlpatterns = [
    path("api/health/", include("apps.common.urls")),
    path("api/files/", include("apps.files.urls")),
]
