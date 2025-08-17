import uuid

from django.contrib.auth import get_user_model
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models

User = get_user_model()

SOURCE_CHOICES = [
    ("google", "Google Open Buildings"),
    ("microsoft", "Microsoft Building Footprints"),
    ("osm", "OpenStreetMap Buildings"),
    ("overture", "Overture Buildings"),
]

OUTPUT_FORMAT_CHOICES = [
    ("geoparquet", "GeoParquet"),
    ("geojson", "GeoJSON"),
    ("shapefile", "Shapefile"),
    ("geopackage", "GeoPackage"),
]

EXPORT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("queued", "Queued"),
    ("processing", "Processing"),
    ("completed", "Completed"),
    ("failed", "Failed"),
]

SOURCE_CONFIG_SCHEMA = {
    "google": {
        "type": "object",
        "properties": {
            "confidence_threshold": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "default": 0.7,
            }
        },
        "additionalProperties": False,
    },
    "microsoft": {
        "type": "object",
        "properties": {
            "region": {
                "type": "string",
                "enum": ["us", "canada", "africa", "australia", "global"],
                "default": "global",
            }
        },
        "additionalProperties": False,
    },
    "osm": {
        "type": "object",
        "properties": {
            "building_types": {
                "type": "array",
                "items": {"type": "string"},
                "default": ["yes", "house", "apartments", "commercial", "industrial"],
            }
        },
        "additionalProperties": False,
    },
    "overture": {
        "type": "object",
        "properties": {
            "include_height": {"type": "boolean", "default": True},
            "min_area": {"type": "number", "minimum": 0, "default": 10},
        },
        "additionalProperties": False,
    },
}


def validate_source_config(source, config):
    if not config:
        return True

    schema = SOURCE_CONFIG_SCHEMA.get(source)
    if not schema:
        raise ValidationError(f"Unknown source: {source}")

    if not isinstance(config, dict):
        raise ValidationError("Source config must be a dictionary")

    return True


class Export(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exports")

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    area_of_interest = gis_models.PolygonField()

    source = ArrayField(models.CharField(max_length=20, choices=SOURCE_CHOICES))
    source_config = models.JSONField(default=dict, blank=True)

    output_format = ArrayField(
        models.CharField(max_length=20, choices=OUTPUT_FORMAT_CHOICES), default=list
    )

    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["is_public", "-created_at"]),
        ]

    def clean(self):
        super().clean()
        # Validate each source if needed
        if isinstance(self.source, list):
            for src in self.source:
                validate_source_config(src, self.source_config)
        else:
            validate_source_config(self.source, self.source_config)

    def __str__(self):
        return f"{self.name} ({', '.join(self.source)})"

    @property
    def latest_run(self):
        return self.runs.first()

    @property
    def is_processing(self):
        return self.runs.filter(status__in=["pending", "queued", "processing"]).exists()


class ExportRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    export = models.ForeignKey(Export, on_delete=models.CASCADE, related_name="runs")

    status = models.CharField(
        max_length=20, choices=EXPORT_STATUS_CHOICES, default="pending"
    )

    results = models.JSONField(default=dict, blank=True)

    output_file = models.FileField(upload_to="exports/%Y/%m/%d/", blank=True, null=True)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    task_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["export", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["task_id"]),
        ]

    def __str__(self):
        return f"{self.export.name} - Run {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def building_count(self):
        return self.results.get("building_count", 0)

    @property
    def file_size(self):
        if self.output_file:
            try:
                return self.output_file.size
            except (OSError, ValueError):
                pass
        return 0
