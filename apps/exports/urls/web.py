from django.urls import path, include
from ..views import web_views

app_name = 'exports'

urlpatterns = [
    path('', web_views.DashboardView.as_view(), name='dashboard'),
    
    path('create/', web_views.CreateExportView.as_view(), name='create'),
    path('<uuid:pk>/', web_views.ExportDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', web_views.EditExportView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', web_views.DeleteExportView.as_view(), name='delete'),
    path('<uuid:pk>/run/', web_views.RunExportView.as_view(), name='run'),
    
    path('runs/<uuid:pk>/', web_views.ExportRunDetailView.as_view(), name='run_detail'),
    path('runs/<uuid:pk>/download/', web_views.DownloadExportView.as_view(), name='download'),
    
    path('public/<uuid:pk>/', web_views.PublicExportView.as_view(), name='public'),
    path('public/<uuid:pk>/download/', web_views.PublicDownloadView.as_view(), name='public_download'),
    
    path('htmx/', include([
        path('map-data/', web_views.MapDataView.as_view(), name='map_data'),
        path('status/<uuid:pk>/', web_views.ExportStatusView.as_view(), name='status'),
        path('runs-list/<uuid:export_id>/', web_views.ExportRunsListView.as_view(), name='runs_list'),
    ])),
]
