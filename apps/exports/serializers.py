from typing import Any, Dict, Optional
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Export, ExportRun


class ExportSerializer(GeoFeatureModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    latest_run = serializers.SerializerMethodField()
    is_processing = serializers.SerializerMethodField()
    share_url = serializers.SerializerMethodField()

    class Meta:
        model = Export
        geo_field = "area_of_interest"
        id_field = False
        fields = [
            "id", "user", "name", "description", "source", "source_config",
            "output_format", "is_public", "share_url", "created_at", "updated_at",
            "latest_run", "is_processing"
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_latest_run(self, obj) -> Optional[Dict[str, Any]]:
        latest_run = obj.latest_run
        if latest_run:
            return {
                "id": str(latest_run.id),
                "status": latest_run.status,
                "created_at": latest_run.created_at,
                "building_count": latest_run.building_count,
                "duration": str(latest_run.duration) if latest_run.duration else None,
            }
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_share_url(self, obj) -> Optional[str]:
        if obj.is_public:
            return f"/public/{obj.id}/"
        return None

    @extend_schema_field(serializers.BooleanField())
    def get_is_processing(self, obj) -> bool:
        return obj.is_processing


class ExportRunSerializer(serializers.ModelSerializer):
    export = serializers.StringRelatedField(read_only=True)
    duration = serializers.SerializerMethodField()
    building_count = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ExportRun
        fields = [
            "id", "export", "status", "results", "started_at", "completed_at",
            "error_message", "task_id", "created_at", "updated_at", "duration",
            "building_count", "file_size", "download_url"
        ]
        read_only_fields = [
            "id", "export", "results", "started_at", "completed_at",
            "error_message", "task_id", "created_at", "updated_at"
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_download_url(self, obj) -> Optional[str]:
        if obj.output_file and obj.status == "completed":
            return f"/api/runs/{obj.id}/download/"
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_duration(self, obj) -> Optional[str]:
        return str(obj.duration) if obj.duration else None

    @extend_schema_field(serializers.IntegerField())
    def get_building_count(self, obj) -> int:
        return obj.building_count

    @extend_schema_field(serializers.IntegerField())
    def get_file_size(self, obj) -> int:
        return obj.file_size


class CreateExportRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportRun
        fields = ["export"]

    def create(self, validated_data):
        validated_data["status"] = "pending"
        return super().create(validated_data)
