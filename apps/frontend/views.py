from django.views.generic import TemplateView


class IndexView(TemplateView):
    """Single page application."""

    template_name = "index.html"
