from django.urls import path
from .views import RulesView, NewVersionView, PreviewView, ExecuteView, ExecutionsView

urlpatterns = [
    path("rules/", RulesView.as_view()),
    path("rules/<uuid:version_id>/versions/", NewVersionView.as_view()),
    path("rules/<uuid:version_id>/preview/", PreviewView.as_view()),
    path("rules/<uuid:version_id>/execute/", ExecuteView.as_view()),
    path("rule-executions/", ExecutionsView.as_view()),
]
