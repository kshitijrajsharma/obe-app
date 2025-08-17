import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from django.contrib.gis.geos import Polygon
from obe.app import download_buildings

logger = logging.getLogger(__name__)


class BuildingStatsGenerator:
    """Generate statistics from building GeoDataFrame"""

    @staticmethod
    def generate_stats(gdf, source: str) -> Dict[str, Any]:
        """Generate dynamic statistics from GeoDataFrame"""
        if gdf is None or gdf.empty:
            return {
                "building_count": 0,
                "total_area_m2": 0,
                "message": "No buildings found",
            }

        stats = {
            "building_count": len(gdf),
            "source": source,
        }

        if hasattr(gdf, "geometry") and not gdf.geometry.empty:
            try:
                gdf_projected = gdf.to_crs("EPSG:3857")
                total_area = gdf_projected.geometry.area.sum()
                stats["total_area_m2"] = float(total_area)
            except Exception as e:
                logger.warning("Could not calculate area: %s", str(e))
                stats["total_area_m2"] = 0

        return stats


class BuildingProcessor:
    """Simplified building processor using OBE library"""

    def __init__(self):
        pass

    def _save_aoi_to_temp_file(self, django_polygon: Polygon) -> str:
        """Save AOI polygon to temporary GeoJSON file"""

        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": json.loads(django_polygon.geojson),
                    "properties": {},
                }
            ],
        }

        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".geojson", delete=False
        )
        temp_path = temp_file.name
        logger.info("Saving AOI to temporary file: %s", temp_path)

        json.dump(geojson_data, temp_file, indent=2)
        temp_file.close()

        return temp_path

    def extract_buildings(
        self,
        area_of_interest: Polygon,
        source: str,
        source_config: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Extract buildings from a single source"""
        temp_aoi_path = None

        try:
            temp_aoi_path = self._save_aoi_to_temp_file(area_of_interest)

            location = None
            if source == "microsoft" and source_config:
                location = source_config.get("location")

            logger.info("Extracting buildings from source: %s", source)

            gdf = download_buildings(
                source=source,
                input_path=temp_aoi_path,
                output_path=None,
                format=None,
                location=location,
            )

            stats = BuildingStatsGenerator.generate_stats(gdf, source)
            stats["gdf"] = gdf
            stats["config_used"] = source_config or {}

            return stats

        except Exception as e:
            raise e
            logger.error("Failed to extract buildings from %s: %s", source, str(e))
            return {
                "building_count": 0,
                "source": source,
                "error": str(e),
                "gdf": None,
            }
        finally:
            if temp_aoi_path:
                try:
                    os.unlink(temp_aoi_path)
                except OSError:
                    pass

    def save_gdf_to_format(
        self, gdf, output_format: str, base_filename: str
    ) -> Dict[str, Any]:
        """Save GeoDataFrame to specified format and return file info"""
        if gdf is None or gdf.empty:
            return {"error": "No data to save"}

        try:
            temp_dir = Path(tempfile.mkdtemp())

            if output_format == "geoparquet":
                file_path = temp_dir / f"{base_filename}.parquet"
                gdf.to_parquet(file_path)
            elif output_format == "geojson":
                file_path = temp_dir / f"{base_filename}.geojson"
                gdf.to_file(file_path, driver="GeoJSON")
            elif output_format == "shapefile":
                file_path = temp_dir / f"{base_filename}.shp"
                gdf.to_file(file_path, driver="ESRI Shapefile")
            elif output_format == "geopackage":
                file_path = temp_dir / f"{base_filename}.gpkg"
                gdf.to_file(file_path, driver="GPKG")
            else:
                raise ValueError(f"Unsupported output format: {output_format}")

            logger.info("Saved %s buildings to %s format", len(gdf), output_format)

            return {
                "file_path": str(file_path),
                "format": output_format,
                "size_bytes": file_path.stat().st_size,
                "building_count": len(gdf),
            }

        except Exception as e:
            logger.error(
                "Failed to save %s in %s format: %s",
                base_filename,
                output_format,
                str(e),
            )
            return {"error": str(e)}
