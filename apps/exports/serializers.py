from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Export, ExportRun


class ExportSerializer(GeoFeatureModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    latest_run = serializers.SerializerMethodField()
    is_processing = serializers.ReadOnlyField()
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = Export
        geo_field = "area_of_interest"
        fields = [
            "id",
            "user",
            "name",
            "description",
            "source",
            "source_config",
            "output_format",
            "is_public",
            "share_url",
            "created_at",
            "updated_at",
            "latest_run",
            "is_processing",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_latest_run(self, obj):
        latest_run = obj.latest_run
        if latest_run:
            return {
                "id": latest_run.id,
                "status": latest_run.status,
                "created_at": latest_run.created_at,
                "building_count": latest_run.building_count,
                "duration": str(latest_run.duration) if latest_run.duration else None,
            }
        return None

    def get_share_url(self, obj):
        if obj.is_public:
            return f"/public/{obj.id}/"
        return None

    def validate_source_config(self, value):
        return value


class ExportRunSerializer(serializers.ModelSerializer):
    export = serializers.StringRelatedField(read_only=True)
    duration = serializers.ReadOnlyField()
    building_count = serializers.ReadOnlyField()
    file_size = serializers.ReadOnlyField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ExportRun
        fields = [
            "id",
            "export",
            "status",
            "results",
            "started_at",
            "completed_at",
            "error_message",
            "task_id",
            "created_at",
            "updated_at",
            "duration",
            "building_count",
            "file_size",
            "download_url",
        ]
        read_only_fields = [
            "id",
            "export",
            "results",
            "started_at",
            "completed_at",
            "error_message",
            "task_id",
            "created_at",
            "updated_at",
        ]

    def get_download_url(self, obj):
        if obj.output_file and obj.status == "completed":
            return f"/exports/runs/{obj.id}/download/"
        return None


class CreateExportRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportRun
        fields = ["export"]

    def create(self, validated_data):
        validated_data["status"] = "pending"
        return super().create(validated_data)
