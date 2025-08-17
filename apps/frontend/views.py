from django.shortcuts import render
from django.views.generic import TemplateView


class IndexView(TemplateView):
    """Single page application."""

    template_name = "index.html"


class ExportDetailView(TemplateView):
    template_name = "export.html"

    def get(self, request, *args, **kwargs):
        return render(
            request, self.template_name, {"export_id": kwargs.get("export_id")}
        )
