from django.urls import path

from .views import (
    CheckRulesView,
    DataHoldersView,
    ProductCheckDetailView,
    ProductChecksView,
)


urlpatterns = [
    path("", ProductChecksView.as_view(), name="product-checks"),
    path("holders/", DataHoldersView.as_view(), name="product-check-holders"),
    path("rules/", CheckRulesView.as_view(), name="product-check-rules"),
    path(
        "<uuid:run_id>/",
        ProductCheckDetailView.as_view(),
        name="product-check-detail",
    ),
]
