import django_filters

from .models import EXPORT_STATUS_CHOICES, Export, ExportRun


class ExportFilter(django_filters.FilterSet):
    """Filter for Export model"""

    is_public = django_filters.BooleanFilter()
    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    updated_after = django_filters.DateTimeFilter(
        field_name="updated_at", lookup_expr="gte"
    )
    updated_before = django_filters.DateTimeFilter(
        field_name="updated_at", lookup_expr="lte"
    )

    class Meta:
        model = Export
        fields = [
            "is_public",
            "created_after",
            "created_before",
            "updated_after",
            "updated_before",
        ]


class ExportRunFilter(django_filters.FilterSet):
    """Filter for ExportRun model"""

    status = django_filters.ChoiceFilter(choices=EXPORT_STATUS_CHOICES)
    created_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    started_after = django_filters.DateTimeFilter(
        field_name="started_at", lookup_expr="gte"
    )
    started_before = django_filters.DateTimeFilter(
        field_name="started_at", lookup_expr="lte"
    )
    completed_after = django_filters.DateTimeFilter(
        field_name="completed_at", lookup_expr="gte"
    )
    completed_before = django_filters.DateTimeFilter(
        field_name="completed_at", lookup_expr="lte"
    )

    class Meta:
        model = ExportRun
        fields = [
            "status",
            "created_after",
            "created_before",
            "started_after",
            "started_before",
            "completed_after",
            "completed_before",
        ]
