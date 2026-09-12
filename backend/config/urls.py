from django.urls import include, path


urlpatterns = [
    path("api/", include("apps.rules.urls")),
    path("api/health/", include("apps.common.urls")),
    path("api/files/", include("apps.files.urls")),
    path("api/regex/", include("apps.regex_engine.urls")),
    path("api/transformations/", include("apps.transformations.urls")),
]
