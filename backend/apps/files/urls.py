from django.urls import path

from .views import FileUploadView, ProcessedFileDownloadView


urlpatterns = [
    path("upload/", FileUploadView.as_view(), name="file-upload"),
    path(
        "processed/<str:processed_file_id>/download/",
        ProcessedFileDownloadView.as_view(),
        name="processed-file-download",
    ),
]
