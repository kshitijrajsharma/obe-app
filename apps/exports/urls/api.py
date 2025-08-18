from django.urls import path

from ..views import api_views
from ..views.api_root import APIRootView
from ..views.api_views import rerun_export

app_name = "api"

urlpatterns = [
    path("", APIRootView.as_view(), name="api-root"),
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
    path(
        "runs/<uuid:pk>/tiles/",
        api_views.ExportRunTilesView.as_view(),
        name="run_tiles",
    ),
    path(
        "exports/rerun/<uuid:export_id>/",
        rerun_export,
        name="rerun-export",
    ),
    # Public exports
    path(
        "public/exports/",
        api_views.PublicExportListView.as_view(),
        name="public_exports",
    ),
    path(
        "public/exports/<uuid:pk>/",
        api_views.PublicExportDetailView.as_view(),
        name="public_export_detail",
    ),
    path(
        "public/exports/<uuid:export_id>/runs/",
        api_views.PublicExportRunListView.as_view(),
        name="public_run_list",
    ),
    path(
        "public/runs/<uuid:pk>/download/",
        api_views.PublicDownloadExportRunView.as_view(),
        name="public_download_run",
    ),
    # Stats
    path(
        "runs/<uuid:pk>/stats/",
        api_views.ExportRunStatsView.as_view(),
        name="run_stats",
    ),
    # Utilities
    path("validate-aoi/", api_views.ValidateAOIView.as_view(), name="validate_aoi"),
    path(
        "source-config-schema/<str:source>/",
        api_views.SourceConfigSchemaView.as_view(),
        name="source_schema",
    ),
]
