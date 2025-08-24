import json

from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view, permission_classes
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


@extend_schema(
    tags=["Exports"],
    summary="List exports or create a new export",
    description="Get a list of exports (public exports for anonymous users, user's exports + public for authenticated users) or create a new export.",
    responses={
        200: ExportSerializer(many=True),
        201: ExportSerializer,
    }
)
class ExportListCreateView(generics.ListCreateAPIView):
    serializer_class = ExportSerializer
    permission_classes = []
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
        if getattr(self, "swagger_fake_view", False):
            return Export.objects.none()
        user = self.request.user
        if user.is_authenticated:
            return Export.objects.filter(Q(user=user) | Q(is_public=True))
        return Export.objects.filter(is_public=True)

    def perform_create(self, serializer):
        export = serializer.save(user=self.request.user)

        export_run = ExportRun.objects.create(export=export)

        export_run.status = "queued"
        export_run.save()

        task = process_export.schedule((str(export_run.id),), delay=1)
        export_run.task_id = task.id
        export_run.save()


@extend_schema(
    tags=["Exports"],
    summary="Retrieve, update or delete an export",
    description="Get details of a specific export, update it, or delete it. Only accessible to export owner or if export is public.",
    responses={
        200: ExportSerializer,
        404: {"description": "Export not found"},
    }
)
class ExportDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExportSerializer
    permission_classes = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Export.objects.none()
        user = self.request.user
        if user.is_authenticated:
            return Export.objects.filter(Q(user=user) | Q(is_public=True))
        return Export.objects.filter(is_public=True)


@extend_schema(
    tags=["Export Runs"],
    summary="List export runs for an export",
    description="Get a paginated list of export runs for a specific export. Supports filtering and ordering.",
    responses={
        200: ExportRunSerializer(many=True),
        404: {"description": "Export not found"},
    }
)
class ExportRunListView(generics.ListAPIView):
    serializer_class = ExportRunSerializer
    permission_classes = []
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ExportRunFilter
    ordering_fields = ["created_at", "started_at", "completed_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExportRun.objects.none()
        export_id = self.kwargs["export_id"]
        user = self.request.user
        if user.is_authenticated:
            return ExportRun.objects.filter(export_id=export_id).filter(
                Q(export__user=user) | Q(export__is_public=True)
            )
        return ExportRun.objects.filter(export_id=export_id, export__is_public=True)


@extend_schema(
    tags=["Export Runs"],
    summary="Create a new export run",
    description="Create a new export run for the specified export. User must own the export.",
    responses={
        201: CreateExportRunSerializer,
        400: {"description": "Export is already being processed"},
        404: {"description": "Export not found"},
    }
)
class ExportRunCreateView(generics.CreateAPIView):
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


@extend_schema(
    tags=["Export Runs"],
    summary="Get export run details",
    description="Retrieve details of a specific export run.",
    responses={
        200: ExportRunSerializer,
        404: {"description": "Export run not found"},
    }
)
class ExportRunDetailView(generics.RetrieveAPIView):
    serializer_class = ExportRunSerializer
    permission_classes = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExportRun.objects.none()
        user = self.request.user
        if user.is_authenticated:
            return ExportRun.objects.filter(
                Q(export__user=user) | Q(export__is_public=True)
            )
        return ExportRun.objects.filter(export__is_public=True)


@extend_schema(
    tags=["Export Runs"],
    summary="Start an export run",
    description="Start processing an export run. The run will be queued for processing.",
    request=None,
    responses={
        200: ExportRunSerializer,
        400: {"description": "Export is already being processed"},
        404: {"description": "Export run not found"},
    }
)
class StartExportRunView(APIView):
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


@extend_schema(
    tags=["Export Runs"],
    summary="Download export output file",
    description="Download the output file of a completed export run.",
    responses={
        200: {
            "description": "Export file download",
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
        400: {"description": "Export run not completed or no output file"},
        404: {"description": "Export run not found"},
    }
)
class DownloadExportRunView(APIView):
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


@extend_schema(
    tags=["Public"],
    summary="Download public export output file",
    description="Download the output file of a completed public export run.",
    responses={
        200: {
            "description": "Export file download",
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
        400: {"description": "Export run not completed or no output file"},
        404: {"description": "Export run not found or not public"},
    }
)
class PublicDownloadExportRunView(APIView):
    permission_classes = []

    def get(self, request, pk):
        try:
            export_run = ExportRun.objects.get(pk=pk, export__is_public=True)

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


@extend_schema(
    tags=["Public"],
    summary="Get public export details",
    description="Retrieve details of a public export.",
    responses={
        200: ExportSerializer,
        404: {"description": "Export not found or not public"},
    }
)
class PublicExportDetailView(generics.RetrieveAPIView):
    serializer_class = ExportSerializer
    permission_classes = []
    lookup_field = "pk"

    def get_queryset(self):
        return Export.objects.filter(is_public=True)


@extend_schema(
    tags=["Public"],
    summary="List export runs for a public export",
    description="Get a paginated list of export runs for a public export.",
    responses={
        200: ExportRunSerializer(many=True),
        404: {"description": "Export not found or not public"},
    }
)
class PublicExportRunListView(generics.ListAPIView):
    serializer_class = ExportRunSerializer
    permission_classes = []
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ExportRunFilter
    ordering_fields = ["created_at", "completed_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        export_id = self.kwargs.get("export_id")
        return ExportRun.objects.filter(export_id=export_id, export__is_public=True)


@extend_schema(
    tags=["Stats"],
    summary="Get export run statistics",
    description="Retrieve detailed statistics for an export run including building count, file size, duration, and more.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "format": "uuid"},
                "export_name": {"type": "string"},
                "status": {"type": "string"},
                "building_count": {"type": "integer"},
                "file_size": {"type": "integer"},
                "duration": {"type": "string", "nullable": True},
                "sources": {"type": "object"},
                "files": {"type": "object"},
                "population": {"type": "object"},
                "created_at": {"type": "string", "format": "date-time"},
                "completed_at": {"type": "string", "format": "date-time", "nullable": True},
                "area_of_interest": {"type": "object"},
                "output_formats": {"type": "array", "items": {"type": "string"}},
            },
        },
        403: {"description": "Access denied"},
        404: {"description": "Export run not found"},
    }
)
class ExportRunStatsView(APIView):
    permission_classes = []

    def get(self, request, pk):
        try:
            export_run = ExportRun.objects.get(pk=pk)

            if (
                not export_run.export.is_public
                and export_run.export.user != request.user
            ):
                if not request.user.is_authenticated:
                    return Response({"error": "Authentication required"}, status=401)
                return Response({"error": "Access denied"}, status=403)

            stats = {
                "run_id": str(export_run.id),
                "export_name": export_run.export.name,
                "status": export_run.status,
                "building_count": export_run.building_count,
                "file_size": export_run.file_size,
                "duration": str(export_run.duration) if export_run.duration else None,
                "sources": export_run.results.get("sources", {}),
                "files": export_run.results.get("files", {}),
                "population": export_run.results.get("population", {}),
                "created_at": export_run.created_at.isoformat(),
                "completed_at": export_run.completed_at.isoformat()
                if export_run.completed_at
                else None,
                "area_of_interest": json.loads(
                    export_run.export.area_of_interest.geojson
                ),
                "output_formats": export_run.export.output_format,
            }

            return Response(stats)

        except ExportRun.DoesNotExist:
            raise Http404("Export run not found")


@extend_schema(
    tags=["Tiles"],
    summary="Download export run tiles",
    description="Download the vector tiles file for an export run.",
    responses={
        200: {
            "description": "Vector tiles file",
            "content": {
                "application/vnd.mapbox-vector-tile": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
        },
        403: {"description": "Access denied"},
        404: {"description": "Export run not found or no tiles available"},
    }
)
class ExportRunTilesView(APIView):
    permission_classes = []

    def get(self, request, pk):
        try:
            export_run = ExportRun.objects.get(pk=pk)

            if (
                not export_run.export.is_public
                and export_run.export.user != request.user
            ):
                if not request.user.is_authenticated:
                    return Response({"error": "Authentication required"}, status=401)
                return Response({"error": "Access denied"}, status=403)

            if not export_run.tiles_file:
                return Response({"error": "No tiles available"}, status=404)

            range_header = request.META.get('HTTP_RANGE')
            
            if range_header:
                import re
                range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2)) if range_match.group(2) else None
                    
                    file_obj = export_run.tiles_file.open('rb')
                    file_size = export_run.tiles_file.size
                    
                    if end is None:
                        end = file_size - 1
                    
                    if start >= file_size or end >= file_size or start > end:
                        from django.http import HttpResponse
                        return HttpResponse(status=416)  # Range Not Satisfiable
                    
                    file_obj.seek(start)
                    content = file_obj.read(end - start + 1)
                    file_obj.close()
                    
                    from django.http import HttpResponse
                    response = HttpResponse(content, status=206, content_type="application/octet-stream")
                    response['Accept-Ranges'] = 'bytes'
                    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                    response['Content-Length'] = str(len(content))
                    response['Access-Control-Allow-Origin'] = '*'
                    response['Access-Control-Allow-Headers'] = 'Range'
                    return response

            response = FileResponse(
                export_run.tiles_file.open("rb"),
                content_type="application/octet-stream",
                as_attachment=False,
                filename=f"export_run_{pk}_tiles.pmtiles"
            )
            response['Accept-Ranges'] = 'bytes'
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'Range'
            return response

        except ExportRun.DoesNotExist:
            raise Http404("Export run not found")


@extend_schema(
    tags=["Utilities"],
    summary="Validate area of interest geometry",
    description="Validate a GeoJSON geometry for use as area of interest. Returns validation status, area in km², and centroid.",
    request={
        "type": "object",
        "properties": {
            "geometry": {
                "type": "object",
                "description": "GeoJSON geometry object (must be a Polygon)"
            }
        },
        "required": ["geometry"]
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "valid": {"type": "boolean"},
                "area_km2": {"type": "number"},
                "centroid": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number"},
                        "lng": {"type": "number"}
                    }
                },
            },
        },
        400: {"description": "Invalid geometry or area too large"},
    }
)
class ValidateAOIView(APIView):
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


@extend_schema(
    tags=["Utilities"],
    summary="Get source configuration schema",
    description="Retrieve the JSON schema for configuring a specific data source.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "schema": {"type": "object"}
            },
        },
        404: {"description": "Unknown source"},
    }
)
class SourceConfigSchemaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, source):
        if source not in SOURCE_CONFIG_SCHEMA:
            return Response(
                {"error": f"Unknown source: {source}"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response({"source": source, "schema": SOURCE_CONFIG_SCHEMA[source]})


@extend_schema(
    tags=["Export Runs"],
    summary="Re-run an export",
    description="Create a new export run for an existing export and start processing.",
    request=None,
    responses={
        201: ExportRunSerializer,
        404: {"description": "Export not found"},
    }
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def rerun_export(request, export_id):
    try:
        export = Export.objects.get(id=export_id)
    except Export.DoesNotExist:
        return Response({"error": "Export not found"}, status=status.HTTP_404_NOT_FOUND)
    run = ExportRun.objects.create(export=export, status="queued")
    process_export.schedule((str(run.id),), delay=1)
    serializer = ExportRunSerializer(run)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Public"],
    summary="List public exports",
    description="Get a paginated list of all public exports available to everyone.",
    responses={
        200: ExportSerializer(many=True),
    }
)
class PublicExportListView(generics.ListAPIView):
    serializer_class = ExportSerializer
    permission_classes = []
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = []
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Export.objects.none()
        return Export.objects.filter(is_public=True)
