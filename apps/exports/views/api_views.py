import json

from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..filters import ExportFilter, ExportRunFilter
from ..models import SOURCE_CONFIG_SCHEMA, Export, ExportRun
from ..serializers import (
    CreateExportRunSerializer,
    ExportRunSerializer,
    ExportSerializer,
)
from ..tasks import process_export


@extend_schema(tags=["Exports"])
class ExportListCreateView(generics.ListCreateAPIView):
    """
    List user's exports or create a new export.

    Supports filtering by source, output_format, is_public, and date ranges.
    Supports searching by name and description.
    """

    serializer_class = ExportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ExportFilter
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "updated_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Check if this is a schema generation request (swagger_fake_view)
        if getattr(self, "swagger_fake_view", False):
            return Export.objects.none()
        return Export.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema(tags=["Exports"])
class ExportDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a specific export.
    """

    serializer_class = ExportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Export.objects.none()
        return Export.objects.filter(user=self.request.user)


@extend_schema(tags=["Export Runs"])
class ExportRunListView(generics.ListAPIView):
    """
    List export runs for a specific export with filtering capabilities.
    """

    serializer_class = ExportRunSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ExportRunFilter
    ordering_fields = ["created_at", "started_at", "completed_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExportRun.objects.none()
        export_id = self.kwargs["export_id"]
        return ExportRun.objects.filter(
            export_id=export_id, export__user=self.request.user
        )


@extend_schema(tags=["Export Runs"])
class ExportRunCreateView(generics.CreateAPIView):
    """
    Create a new export run for a specific export.
    """

    serializer_class = CreateExportRunSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        export_id = self.kwargs["export_id"]
        try:
            export = Export.objects.get(id=export_id, user=self.request.user)
        except Export.DoesNotExist:
            raise ValidationError("Export not found")

        if export.is_processing:
            raise ValidationError("Export is already being processed")

        serializer.save(export=export)


@extend_schema(tags=["Export Runs"])
class ExportRunDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of a specific export run.
    """

    serializer_class = ExportRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExportRun.objects.none()
        return ExportRun.objects.filter(export__user=self.request.user)


@extend_schema(tags=["Export Runs"])
class StartExportRunView(APIView):
    """
    Start processing an export run.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            export_run = ExportRun.objects.get(pk=pk, export__user=request.user)

            if export_run.export.is_processing:
                return Response(
                    {"error": "Export is already being processed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            export_run.status = "queued"
            export_run.save()

            task = process_export.schedule((str(export_run.id),), delay=1)
            export_run.task_id = task.id
            export_run.save()

            serializer = ExportRunSerializer(export_run)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ExportRun.DoesNotExist:
            return Response(
                {"error": "Export run not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(tags=["Export Runs"])
class DownloadExportRunView(APIView):
    """
    Download the result file of a completed export run.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            export_run = ExportRun.objects.get(pk=pk, export__user=request.user)

            if export_run.status != "completed" or not export_run.output_file:
                return Response(
                    {"error": "Export run is not completed or has no output file"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response = FileResponse(
                export_run.output_file.open("rb"),
                as_attachment=True,
                filename=export_run.output_file.name.split("/")[-1],
            )
            return response

        except ExportRun.DoesNotExist:
            raise Http404("Export run not found")


@extend_schema(tags=["Utilities"])
class ValidateAOIView(APIView):
    """
    Validate area of interest geometry and get area information.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            geojson_data = request.data.get("geometry")
            if not geojson_data:
                return Response(
                    {"error": "geometry field is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            geometry = GEOSGeometry(json.dumps(geojson_data))

            if not geometry.valid:
                return Response(
                    {"error": "Invalid geometry"}, status=status.HTTP_400_BAD_REQUEST
                )

            if geometry.geom_type != "Polygon":
                return Response(
                    {"error": "Geometry must be a Polygon"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            area_deg2 = geometry.area
            area_km2 = area_deg2 * 111.32 * 111.32

            if area_km2 > 10000:
                return Response(
                    {"error": "Area too large (max 10,000 km²)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {
                    "valid": True,
                    "area_km2": round(area_km2, 2),
                    "centroid": {
                        "lat": geometry.centroid.y,
                        "lng": geometry.centroid.x,
                    },
                }
            )

        except (ValueError, TypeError, ValidationError) as e:
            return Response(
                {"error": f"Invalid geometry: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["Utilities"])
class SourceConfigSchemaView(APIView):
    """
    Get configuration schema for a specific data source.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, source):
        if source not in SOURCE_CONFIG_SCHEMA:
            return Response(
                {"error": f"Unknown source: {source}"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response({"source": source, "schema": SOURCE_CONFIG_SCHEMA[source]})


@extend_schema(tags=["Public"])
class PublicExportListView(generics.ListAPIView):
    """
    List all public exports (no authentication required).
    """

    serializer_class = ExportSerializer
    permission_classes = []
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["source", "output_format"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Export.objects.none()
        return Export.objects.filter(is_public=True)
