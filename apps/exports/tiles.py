import json
import os
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile


def generate_pmtiles_from_multiple_geojson(geojson_paths, export_run):
    """Generate PMTiles from multiple GeoJSON files by merging them with tippecanoe."""
    tiles_dir = Path(settings.MEDIA_ROOT) / "tiles"
    tiles_dir.mkdir(exist_ok=True)

    output_path = tiles_dir / f"{export_run.id}.pmtiles"

    cmd = [
        "tippecanoe",
        "--output",
        str(output_path),
        "--layer",
        "buildings",
        "--minimum-zoom",
        "5",
        "--maximum-zoom",
        "18",
        "--drop-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        "--force",
    ]
    
    cmd.extend(geojson_paths)

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Tippecanoe failed: {result.stderr}")

    if not output_path.exists():
        raise RuntimeError(
            f"Tippecanoe succeeded but output file {output_path} was not created"
        )

    with open(output_path, "rb") as f:
        file_content = ContentFile(f.read())
        filename = f"{export_run.id}.pmtiles"
        export_run.tiles_file.save(filename, file_content)
        export_run.refresh_from_db()

    return output_path


def generate_pmtiles_from_geojson(geojson_path, export_run):
    tiles_dir = Path(settings.MEDIA_ROOT) / "tiles"
    tiles_dir.mkdir(exist_ok=True)

    output_path = tiles_dir / f"{export_run.id}.pmtiles"

    cmd = [
        "tippecanoe",
        "--output",
        str(output_path),
        "--layer",
        "buildings",
        "--minimum-zoom",
        "5",
        "--maximum-zoom",
        "18",
        "--drop-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        "--force",
        geojson_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Tippecanoe failed: {result.stderr}")

    if not output_path.exists():
        raise RuntimeError(
            f"Tippecanoe succeeded but output file {output_path} was not created"
        )

    with open(output_path, "rb") as f:
        file_content = ContentFile(f.read())
        filename = f"{export_run.id}.pmtiles"
        export_run.tiles_file.save(filename, file_content)
        export_run.refresh_from_db()

    return output_path


def generate_pmtiles_from_gdf(gdf, export_run):
    if gdf is None or gdf.empty:
        raise ValueError("GeoDataFrame is None or empty")

    tiles_dir = Path(settings.MEDIA_ROOT) / "tiles"
    tiles_dir.mkdir(exist_ok=True)

    output_path = tiles_dir / f"{export_run.id}.pmtiles"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".geojsonl", delete=False
    ) as temp_file:
        temp_path = temp_file.name

        try:
            _write_geojsonl(gdf, temp_file)
            temp_file.flush()

            cmd = [
                "tippecanoe",
                "--output",
                str(output_path),
                "--layer",
                "buildings",
                "--minimum-zoom",
                "5",
                "--maximum-zoom",
                "18",
                "--drop-densest-as-needed",
                "--extend-zooms-if-still-dropping",
                "--force",
                temp_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"Tippecanoe failed: {result.stderr}")

            # Check if the output file was actually created
            if not output_path.exists():
                raise RuntimeError(
                    f"Tippecanoe succeeded but output file {output_path} was not created"
                )

            # Save the tiles file to the Django FileField
            with open(output_path, "rb") as f:
                file_content = ContentFile(f.read())
                filename = f"{export_run.id}.pmtiles"
                export_run.tiles_file.save(filename, file_content)
                export_run.refresh_from_db()  # Refresh to make sure the save worked

            return output_path

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


def _write_geojsonl(gdf, file_handle):
    if gdf is None or gdf.empty:
        return

    for _, row in gdf.iterrows():
        try:
            geometry_json = row.geometry.to_json()
            if geometry_json and geometry_json != "null":
                feature = {
                    "type": "Feature",
                    "geometry": json.loads(geometry_json),
                    "properties": {
                        k: v
                        for k, v in row.items()
                        if k != "geometry" and v is not None
                    },
                }
                file_handle.write(json.dumps(feature) + "\n")
        except (AttributeError, TypeError, json.JSONDecodeError):
            continue


def is_tippecanoe_available():
    try:
        subprocess.run(["tippecanoe", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
