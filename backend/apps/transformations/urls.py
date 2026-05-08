from django.urls import path

from .views import PhoneNormalizeView, PiiRedactView


urlpatterns = [
    path("pii-redact/", PiiRedactView.as_view(), name="transformation-pii-redact"),
    path(
        "phone-normalize/",
        PhoneNormalizeView.as_view(),
        name="transformation-phone-normalize",
    ),
]
