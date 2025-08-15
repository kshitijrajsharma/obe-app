import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)
from django_htmx.http import HttpResponseClientRedirect

from ..models import (
    OUTPUT_FORMAT_CHOICES,
    SOURCE_CHOICES,
    SOURCE_CONFIG_SCHEMA,
    Export,
    ExportRun,
)
from ..tasks import process_export


class DashboardView(LoginRequiredMixin, ListView):
    model = Export
    template_name = "exports/dashboard.html"
    context_object_name = "exports"
    paginate_by = 10

    def get_queryset(self):
        return Export.objects.filter(user=self.request.user).prefetch_related("runs")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        exports = self.get_queryset()
        context.update(
            {
                "total_exports": exports.count(),
                "processing_exports": exports.filter(
                    runs__status__in=["pending", "queued", "processing"]
                )
                .distinct()
                .count(),
                "completed_exports": exports.filter(runs__status="completed")
                .distinct()
                .count(),
                "source_choices": SOURCE_CHOICES,
                "output_format_choices": OUTPUT_FORMAT_CHOICES,
            }
        )

        return context


class CreateExportView(LoginRequiredMixin, CreateView):
    model = Export
    template_name = "exports/create.html"
    fields = [
        "name",
        "description",
        "source",
        "source_config",
        "output_format",
        "is_public",
    ]

    def form_valid(self, form):
        form.instance.user = self.request.user

        aoi_geojson = self.request.POST.get("area_of_interest")
        if aoi_geojson:
            try:
                from django.contrib.gis.geos import GEOSGeometry

                form.instance.area_of_interest = GEOSGeometry(aoi_geojson)
            except Exception as e:
                form.add_error("area_of_interest", f"Invalid geometry: {str(e)}")
                return self.form_invalid(form)

        messages.success(self.request, "Export configuration created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("exports:detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "source_choices": SOURCE_CHOICES,
                "output_format_choices": OUTPUT_FORMAT_CHOICES,
                "source_config_schemas": SOURCE_CONFIG_SCHEMA,
            }
        )
        return context


class ExportDetailView(LoginRequiredMixin, DetailView):
    model = Export
    template_name = "exports/detail.html"
    context_object_name = "export"

    def get_queryset(self):
        return Export.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["runs"] = self.object.runs.all()[:10]
        return context


class EditExportView(LoginRequiredMixin, UpdateView):
    model = Export
    template_name = "exports/edit.html"
    fields = [
        "name",
        "description",
        "source",
        "source_config",
        "output_format",
        "is_public",
    ]

    def get_queryset(self):
        return Export.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse("exports:detail", kwargs={"pk": self.object.pk})


class DeleteExportView(LoginRequiredMixin, DeleteView):
    model = Export
    template_name = "exports/delete.html"
    success_url = reverse_lazy("exports:dashboard")

    def get_queryset(self):
        return Export.objects.filter(user=self.request.user)


class RunExportView(LoginRequiredMixin, View):
    def post(self, request, pk):
        export = get_object_or_404(Export, pk=pk, user=request.user)

        if export.is_processing:
            messages.warning(request, "Export is already being processed.")
            return redirect("exports:detail", pk=pk)

        export_run = ExportRun.objects.create(export=export, status="queued")

        task = process_export.schedule((str(export_run.id),), delay=1)
        export_run.task_id = task.id
        export_run.save()

        messages.success(request, "Export processing started!")

        if request.htmx:
            return HttpResponseClientRedirect(
                reverse("exports:detail", kwargs={"pk": pk})
            )

        return redirect("exports:detail", pk=pk)


class ExportRunDetailView(LoginRequiredMixin, DetailView):
    model = ExportRun
    template_name = "exports/run_detail.html"
    context_object_name = "run"

    def get_queryset(self):
        return ExportRun.objects.filter(export__user=self.request.user)


class DownloadExportView(LoginRequiredMixin, View):
    def get(self, request, pk):
        run = get_object_or_404(ExportRun, pk=pk, export__user=request.user)

        if not run.output_file or run.status != "completed":
            raise Http404("Export file not available")

        response = FileResponse(
            run.output_file,
            as_attachment=True,
            filename=run.output_file.name.split("/")[-1],
        )

        return response


class PublicExportView(DetailView):
    model = Export
    template_name = "exports/public.html"
    context_object_name = "export"

    def get_object(self):
        export_id = self.kwargs["pk"]
        try:
            export = Export.objects.get(id=export_id)
            if not export.is_public:
                raise Http404("Export is private")
            return export
        except Export.DoesNotExist:
            raise Http404("Export not found")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["runs"] = self.object.runs.filter(status="completed")[:5]
        return context


class PublicDownloadView(View):
    def get(self, request, pk):
        try:
            export = Export.objects.get(id=pk)
            if not export.is_public:
                raise Http404("Export is private")
        except Export.DoesNotExist:
            raise Http404("Export not found")

        run = export.runs.filter(status="completed").first()
        if not run or not run.output_file:
            raise Http404("Export file not available")

        response = FileResponse(
            run.output_file,
            as_attachment=True,
            filename=run.output_file.name.split("/")[-1],
        )

        return response


class MapDataView(LoginRequiredMixin, View):
    def get(self, request):
        export_id = request.GET.get("export_id")
        if not export_id:
            return JsonResponse({"error": "export_id required"}, status=400)

        try:
            export = Export.objects.get(id=export_id, user=request.user)
            latest_run = export.latest_run

            if not latest_run or latest_run.status != "completed":
                return JsonResponse({"status": "no_data"})

            data = {
                "status": "success",
                "aoi": json.loads(export.area_of_interest.geojson),
                "building_count": latest_run.building_count,
                "results": latest_run.results,
            }

            return JsonResponse(data)

        except Export.DoesNotExist:
            return JsonResponse({"error": "Export not found"}, status=404)


class ExportStatusView(LoginRequiredMixin, View):
    def get(self, request, pk):
        try:
            export = Export.objects.get(id=pk, user=request.user)
            latest_run = export.latest_run

            if not latest_run:
                return render(
                    request, "exports/htmx/status.html", {"status": "no_runs"}
                )

            context = {
                "export": export,
                "run": latest_run,
                "is_processing": export.is_processing,
            }

            return render(request, "exports/htmx/status.html", context)

        except Export.DoesNotExist:
            return HttpResponse("Export not found", status=404)


class ExportRunsListView(LoginRequiredMixin, ListView):
    model = ExportRun
    template_name = "exports/htmx/runs_list.html"
    context_object_name = "runs"

    def get_queryset(self):
        export_id = self.kwargs["export_id"]
        return ExportRun.objects.filter(
            export_id=export_id, export__user=self.request.user
        ).order_by("-created_at")[:10]
