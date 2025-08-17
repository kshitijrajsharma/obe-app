import logging
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from huey.contrib.djhuey import task

from .models import ExportRun
from .processors import BuildingProcessor

logger = logging.getLogger(__name__)


@task()
def process_export(export_run_id: str) -> Dict[str, Any]:
    try:
        export_run = ExportRun.objects.get(id=export_run_id)
        export_run.status = "processing"
        export_run.started_at = datetime.now()
        export_run.save()

        logger.info("Starting export processing for run %s", export_run_id)

        export = export_run.export
        sources = export.source if isinstance(export.source, list) else [export.source]
        output_formats = (
            export.output_format
            if isinstance(export.output_format, list)
            else [export.output_format]
        )

        processor = BuildingProcessor()

        source_results = {}
        all_files = {}
        total_building_count = 0

        for source in sources:
            logger.info("Processing source: %s", source)

            result = processor.extract_buildings(
                area_of_interest=export.area_of_interest,
                source=source,
                source_config=export.source_config,
            )

            if result.get("error"):
                source_results[source] = result
                continue

            building_count = result.get("building_count", 0)
            total_building_count += building_count

            gdf = result.pop("gdf", None)
            source_results[source] = result

            if gdf is not None and not gdf.empty:
                source_files = {}
                for output_format in output_formats:
                    logger.info("Generating %s file for %s", output_format, source)

                    file_info = processor.save_gdf_to_format(
                        gdf, output_format, f"{source}_buildings"
                    )

                    if not file_info.get("error"):
                        source_files[output_format] = file_info

                all_files[source] = source_files

            logger.info("Processed %s buildings from %s", building_count, source)

        if total_building_count == 0:
            export_run.results = {
                "status": "completed",
                "building_count": 0,
                "message": "No buildings found from any source",
                "sources": source_results,
            }
            export_run.status = "completed"
            export_run.completed_at = datetime.now()
            export_run.save()

            logger.info(
                "Export processing completed for run %s - no data found", export_run_id
            )
            return {"status": "completed", "building_count": 0}

        output_file_path = None
        if all_files:
            output_file_path = _package_files(
                all_files, export.name, export_run.created_at
            )

            if output_file_path:
                with open(output_file_path, "rb") as f:
                    file_content = ContentFile(f.read())
                    filename = Path(output_file_path).name
                    export_run.output_file.save(filename, file_content)

                try:
                    os.unlink(output_file_path)
                except OSError:
                    pass

        for source_files in all_files.values():
            for file_info in source_files.values():
                if file_info.get("file_path"):
                    try:
                        os.unlink(file_info["file_path"])
                    except OSError:
                        pass

        final_results = {
            "status": "completed",
            "building_count": total_building_count,
            "sources": source_results,
            "output_formats": output_formats,
            "files": all_files,
        }

        export_run.results = final_results
        export_run.status = "completed"
        export_run.completed_at = datetime.now()
        export_run.save()

        logger.info("Export processing completed for run %s", export_run_id)

        if export_run.export.user.email_notifications and export_run.export.user.email:
            send_export_completion_email.schedule((export_run_id,), delay=30)

        return {
            "status": "completed",
            "building_count": total_building_count,
            "file_size": export_run.file_size,
        }

    except ExportRun.DoesNotExist:
        logger.error("ExportRun %s not found", export_run_id)
        return {"status": "failed", "error": "Export run not found"}

    except Exception as e:
        logger.error("Export processing failed for run %s: %s", export_run_id, str(e))

        try:
            export_run = ExportRun.objects.get(id=export_run_id)
            export_run.status = "failed"
            export_run.error_message = str(e)
            export_run.completed_at = datetime.now()
            export_run.save()
        except ExportRun.DoesNotExist:
            pass

        return {"status": "failed", "error": str(e)}


def _package_files(all_files: Dict, export_name: str, created_at) -> str:
    """Package all files into a compressed zip archive"""
    temp_dir = Path(tempfile.mkdtemp())
    zip_path = temp_dir / f"{export_name}_{created_at.strftime('%Y%m%d_%H%M%S')}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for source, source_files in all_files.items():
            for format_name, file_info in source_files.items():
                file_path = Path(file_info["file_path"])
                archive_name = f"{source}_{format_name}{file_path.suffix}"
                zipf.write(file_path, archive_name)

    return str(zip_path)


@task()
def send_export_completion_email(export_run_id: str) -> bool:
    try:
        export_run = ExportRun.objects.get(id=export_run_id)
        user = export_run.export.user

        if not user.email or not user.email_notifications:
            return False

        context = {
            "user": user,
            "export": export_run.export,
            "run": export_run,
            "site_name": getattr(settings, "SITE_NAME", "Building Extractor"),
            "download_url": f"{settings.SITE_URL}/exports/runs/{export_run.id}/download/",
        }

        subject = f"Export Complete: {export_run.export.name}"

        html_message = render_to_string("emails/export_complete.html", context)
        text_message = render_to_string("emails/export_complete.txt", context)

        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(
            "Sent completion email to %s for export run %s", user.email, export_run_id
        )
        return True

    except ExportRun.DoesNotExist:
        logger.error("ExportRun %s not found for email notification", export_run_id)
        return False

    except Exception as e:
        logger.error(
            "Failed to send email for export run %s: %s", export_run_id, str(e)
        )
        return False


@task()
def cleanup_old_exports():
    from datetime import timedelta

    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=30)

    old_runs = ExportRun.objects.filter(
        created_at__lt=cutoff_date, export__is_public=False
    )

    deleted_files = 0
    deleted_runs = 0

    for run in old_runs:
        if run.output_file:
            try:
                run.output_file.delete()
                deleted_files += 1
            except Exception as e:
                logger.warning("Failed to delete file for run %s: %s", run.id, str(e))

        run.delete()
        deleted_runs += 1

    logger.info(
        "Cleanup completed: %s runs and %s files deleted", deleted_runs, deleted_files
    )

    return {"deleted_runs": deleted_runs, "deleted_files": deleted_files}
