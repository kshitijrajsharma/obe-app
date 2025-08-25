import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from huey.contrib.djhuey import task

from .models import ExportRun
from .population import PopulationEstimator
from .processors import BuildingProcessor
from .tiles import (
    generate_pmtiles_from_gdf,
    generate_pmtiles_from_geojson,
    generate_pmtiles_from_multiple_geojson,
    is_tippecanoe_available,
)

logger = logging.getLogger(__name__)


@task()
def process_export(export_run_id: str) -> Dict[str, Any]:
    try:
        export_run = ExportRun.objects.get(id=export_run_id)
        export_run.status = "processing"
        export_run.started_at = timezone.now()
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
                geojson_file_path = None

                for output_format in output_formats:
                    if output_format == "tiles":
                        continue

                    logger.info("Generating %s file for %s", output_format, source)

                    file_info = processor.save_gdf_to_format(
                        gdf, output_format, f"{source}_buildings"
                    )

                    if not file_info.get("error"):
                        source_files[output_format] = file_info
                        if output_format == "geojson":
                            geojson_file_path = file_info.get("file_path")

                all_files[source] = source_files
                if geojson_file_path:
                    source_results[source]["geojson_path"] = geojson_file_path
                source_results[source]["has_data"] = True

            logger.info("Processed %s buildings from %s", building_count, source)

        if total_building_count == 0:
            logger.info("No buildings found in any source, completing export run")
            export_run.results = {
                "status": "completed",
                "message": "No buildings found from any source",
                "sources": source_results,
            }
            export_run.status = "completed"
            export_run.completed_at = timezone.now()
            export_run.save()

            logger.info(
                "Export processing completed for run %s - no data found", export_run_id
            )
            return {"status": "completed"}

        final_results = {
            "status": "completed",
            "sources": source_results,
            "output_formats": output_formats,
            "files": all_files,
        }

        population_data = PopulationEstimator.estimate_population(
            export.area_of_interest
        )
        if population_data:
            final_results["population"] = population_data

            pop_total = population_data.get("population_estimate", 0)
            
            final_results["population_stats"] = {
                "source_completeness": _analyze_source_completeness(
                    source_results, pop_total
                ),
            }

        if is_tippecanoe_available() and total_building_count > 0:
            try:
                existing_geojson_paths = []
                gdfs_for_merge = []

                for source in sources:
                    result = source_results.get(source, {})
                    if result.get("geojson_path"):
                        existing_geojson_paths.append(result["geojson_path"])
                    elif result.get("has_data"):
                        gdf_result = processor.extract_buildings(
                            area_of_interest=export.area_of_interest,
                            source=source,
                            source_config=export.source_config,
                        )
                        if (
                            not gdf_result.get("error")
                            and gdf_result.get("gdf") is not None
                        ):
                            gdfs_for_merge.append(gdf_result["gdf"])

                if existing_geojson_paths and len(existing_geojson_paths) == 1:
                    generate_pmtiles_from_geojson(existing_geojson_paths[0], export_run)
                elif existing_geojson_paths and len(existing_geojson_paths) > 1:
                    generate_pmtiles_from_multiple_geojson(existing_geojson_paths, export_run)
                elif gdfs_for_merge:
                    combined_gdf = gdfs_for_merge[0]
                    for gdf in gdfs_for_merge[1:]:
                        combined_gdf = combined_gdf.append(gdf, ignore_index=True)
                    generate_pmtiles_from_gdf(combined_gdf, export_run)

                final_results["tiles_generated"] = True
                final_results["tiles_available"] = True

            except Exception as e:
                logger.error("Tile generation failed: %s", e)
                final_results["tiles_error"] = str(e)

        output_file_path = None
        if all_files:
            output_file_path = _package_files(
                all_files, export.name, export_run.created_at, export_run
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

        logger.info(final_results)

        export_run.results = final_results
        export_run.status = "completed"
        export_run.completed_at = timezone.now()
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
            export_run.completed_at = timezone.now()
            export_run.save()
        except ExportRun.DoesNotExist:
            pass

        return {"status": "failed", "error": str(e)}


def _package_files(
    all_files: Dict, export_name: str, created_at, export_run=None
) -> str:
    temp_dir = Path(tempfile.mkdtemp())
    zip_path = temp_dir / f"{export_name}_{created_at.strftime('%Y%m%d_%H%M%S')}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for source, source_files in all_files.items():
            for format_name, file_info in source_files.items():
                file_path = Path(file_info["file_path"])
                archive_name = f"{source}_{format_name}{file_path.suffix}"
                zipf.write(file_path, archive_name)

        if export_run and export_run.tiles_file:
            try:
                tiles_file_path = export_run.tiles_file.path
                if Path(tiles_file_path).exists():
                    archive_name = "vector_tiles.pmtiles"
                    zipf.write(tiles_file_path, archive_name)
                    logger.info("Added PMTiles file to zip: %s", archive_name)
                else:
                    logger.warning(
                        "PMTiles file path does not exist: %s", tiles_file_path
                    )
            except (AttributeError, ValueError, OSError) as e:
                logger.warning("Could not add PMTiles to zip: %s", e)

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


def _classify_building_density(population, building_count):
    if population == 0 or building_count == 0:
        return "unknown"

    people_per_building = population / building_count

    if people_per_building < 2:
        return "low_density"
    elif people_per_building < 5:
        return "medium_density"
    elif people_per_building < 10:
        return "high_density"
    else:
        return "very_high_density"


def _analyze_source_completeness(source_results, population):
    completeness = {}

    for source, result in source_results.items():
        building_count = result.get("building_count", 0)
        if building_count > 0 and population > 0:
            buildings_per_capita = building_count / population

            completeness[source] = {
                "building_count": building_count,
                "buildings_per_capita": round(buildings_per_capita * 1000, 3),
                "estimated_coverage": _estimate_coverage_level(buildings_per_capita),
            }

    return completeness


def _estimate_coverage_level(buildings_per_capita):
    if buildings_per_capita < 0.1:
        return "very_low"
    elif buildings_per_capita < 0.2:
        return "low"
    elif buildings_per_capita < 0.4:
        return "moderate"
    elif buildings_per_capita < 0.6:
        return "high"
    else:
        return "excellent"
