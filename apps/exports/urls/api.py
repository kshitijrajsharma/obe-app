from django.urls import path

from ..views import api_views

app_name = "api"

urlpatterns = [
    # Export CRUD
    path("exports/", api_views.ExportListCreateView.as_view(), name="export_list"),
    path(
        "exports/<uuid:pk>/", api_views.ExportDetailView.as_view(), name="export_detail"
    ),
    # Export runs
    path(
        "exports/<uuid:export_id>/runs/",
        api_views.ExportRunListView.as_view(),
        name="run_list",
    ),
    path(
        "exports/<uuid:export_id>/runs/create/",
        api_views.ExportRunCreateView.as_view(),
        name="run_create",
    ),
    path("runs/<uuid:pk>/", api_views.ExportRunDetailView.as_view(), name="run_detail"),
    path(
        "runs/<uuid:pk>/start/",
        api_views.StartExportRunView.as_view(),
        name="start_run",
    ),
    path(
        "runs/<uuid:pk>/download/",
        api_views.DownloadExportRunView.as_view(),
        name="download_run",
    ),
    # Public exports
    path(
        "public/exports/",
        api_views.PublicExportListView.as_view(),
        name="public_exports",
    ),
    # Utilities
    path("validate-aoi/", api_views.ValidateAOIView.as_view(), name="validate_aoi"),
    path(
        "source-config-schema/<str:source>/",
        api_views.SourceConfigSchemaView.as_view(),
        name="source_schema",
    ),
]
