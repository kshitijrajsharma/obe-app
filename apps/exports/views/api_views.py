import json

from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import SOURCE_CONFIG_SCHEMA, Export, ExportRun
from ..serializers import ExportRunSerializer, ExportSerializer
from ..tasks import process_export


class ExportListCreateView(generics.ListCreateAPIView):
    serializer_class = ExportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Export.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ExportDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Export.objects.filter(user=self.request.user)


class ExportRunListView(generics.ListAPIView):
    serializer_class = ExportRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        export_id = self.kwargs["export_id"]
        return ExportRun.objects.filter(
            export_id=export_id, export__user=self.request.user
        ).order_by("-created_at")


class ExportRunDetailView(generics.RetrieveAPIView):
    serializer_class = ExportRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExportRun.objects.filter(export__user=self.request.user)


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


class SourceConfigSchemaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, source):
        if source not in SOURCE_CONFIG_SCHEMA:
            return Response(
                {"error": f"Unknown source: {source}"}, status=status.HTTP_404_NOT_FOUND
            )

        return Response({"source": source, "schema": SOURCE_CONFIG_SCHEMA[source]})
