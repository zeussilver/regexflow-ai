from django.urls import path

from .views import RegexGenerateView, RegexReplaceView


urlpatterns = [
    path("generate/", RegexGenerateView.as_view(), name="regex-generate"),
    path("replace/", RegexReplaceView.as_view(), name="regex-replace"),
]
