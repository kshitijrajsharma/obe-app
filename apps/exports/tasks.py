import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from huey.contrib.djhuey import task

from .models import ExportRun
from .processors import get_processor

logger = logging.getLogger(__name__)


@task()
def process_export(export_run_id: str) -> Dict[str, Any]:
    try:
        export_run = ExportRun.objects.get(id=export_run_id)
        export_run.status = "processing"
        export_run.started_at = datetime.now()
        export_run.save()

        logger.info(f"Starting export processing for run {export_run_id}")

        processor = get_processor(export_run.export.source)

        result = processor.process(
            area_of_interest=export_run.export.area_of_interest,
            source_config=export_run.export.source_config,
            output_format=export_run.export.output_format,
        )

        if result.get("file_path"):
            file_path = Path(result["file_path"])
            with open(file_path, "rb") as f:
                file_content = ContentFile(f.read())
                filename = f"{export_run.export.name}_{export_run.created_at.strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
                export_run.output_file.save(filename, file_content)

            os.unlink(file_path)

        export_run.results = result
        export_run.status = "completed"
        export_run.completed_at = datetime.now()
        export_run.save()

        logger.info(f"Export processing completed for run {export_run_id}")

        if export_run.export.user.email_notifications and export_run.export.user.email:
            send_export_completion_email.schedule((export_run_id,), delay=30)

        return {
            "status": "completed",
            "building_count": result.get("building_count", 0),
            "file_size": export_run.file_size,
        }

    except ExportRun.DoesNotExist:
        logger.error(f"ExportRun {export_run_id} not found")
        return {"status": "failed", "error": "Export run not found"}

    except Exception as e:
        logger.error(f"Export processing failed for run {export_run_id}: {str(e)}")

        try:
            export_run = ExportRun.objects.get(id=export_run_id)
            export_run.status = "failed"
            export_run.error_message = str(e)
            export_run.completed_at = datetime.now()
            export_run.save()
        except ExportRun.DoesNotExist:
            pass

        return {"status": "failed", "error": str(e)}


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
            f"Sent completion email to {user.email} for export run {export_run_id}"
        )
        return True

    except ExportRun.DoesNotExist:
        logger.error(f"ExportRun {export_run_id} not found for email notification")
        return False

    except Exception as e:
        logger.error(f"Failed to send email for export run {export_run_id}: {str(e)}")
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
                logger.warning(f"Failed to delete file for run {run.id}: {str(e)}")

        run.delete()
        deleted_runs += 1

    logger.info(
        f"Cleanup completed: {deleted_runs} runs and {deleted_files} files deleted"
    )

    return {"deleted_runs": deleted_runs, "deleted_files": deleted_files}
