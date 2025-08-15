from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Export, ExportRun


@admin.register(Export)
class ExportAdmin(GISModelAdmin):
    list_display = [
        "name",
        "user",
        "source",
        "output_format",
        "is_public",
        "created_at",
        "latest_run_status",
    ]
    list_filter = ["source", "output_format", "is_public", "created_at"]
    search_fields = ["name", "description", "user__email"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "description", "user")}),
        (
            "Configuration",
            {
                "fields": (
                    "source",
                    "source_config",
                    "output_format",
                    "area_of_interest",
                )
            },
        ),
        ("Sharing", {"fields": ("is_public",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def latest_run_status(self, obj):
        latest_run = obj.latest_run
        if latest_run:
            return latest_run.status
        return "No runs"

    latest_run_status.short_description = "Latest Status"


@admin.register(ExportRun)
class ExportRunAdmin(admin.ModelAdmin):
    list_display = [
        "export_name",
        "status",
        "building_count",
        "started_at",
        "completed_at",
        "duration_display",
    ]
    list_filter = ["status", "export__source", "created_at"]
    search_fields = ["export__name", "export__user__email"]
    readonly_fields = [
        "task_id",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
        "duration_display",
        "building_count",
    ]

    fieldsets = (
        ("Export Information", {"fields": ("export", "status")}),
        (
            "Processing",
            {"fields": ("task_id", "started_at", "completed_at", "duration_display")},
        ),
        ("Results", {"fields": ("building_count", "results", "output_file")}),
        ("Error Information", {"fields": ("error_message",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def export_name(self, obj):
        return obj.export.name

    export_name.short_description = "Export"

    def duration_display(self, obj):
        return str(obj.duration) if obj.duration else "N/A"

    duration_display.short_description = "Duration"
