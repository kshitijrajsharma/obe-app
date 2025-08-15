# OBE API

Django REST API for extracting building footprints from multiple data sources.

## Data Sources

- Google Open Buildings
- Microsoft Building Footprints  
- OpenStreetMap Buildings
- Overture Buildings

## Output Formats

- GeoParquet
- GeoJSON
- Shapefile
- GeoPackage

## Requirements

- Python 3.11+
- PostgreSQL with PostGIS
- Redis
- GDAL/GEOS libraries
- uv package manager

## Setup

```bash
git clone <repository>
cd obe-app
./setup.sh
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

## Run

```bash
uv run python manage.py runserver
uv run python manage.py run_huey
```

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Get access token
- `POST /api/auth/refresh/` - Refresh token
- `POST /api/auth/register/` - Create account
- `GET /api/auth/profile/` - Get user profile

### Exports
- `GET /api/exports/` - List user exports
- `POST /api/exports/` - Create export
- `GET /api/exports/{id}/` - Get export details
- `PUT /api/exports/{id}/` - Update export
- `DELETE /api/exports/{id}/` - Delete export

### Export Runs
- `GET /api/exports/{export_id}/runs/` - List runs for export
- `POST /api/exports/{export_id}/runs/create/` - Create new run
- `GET /api/runs/{id}/` - Get run details
- `POST /api/runs/{id}/start/` - Start processing
- `GET /api/runs/{id}/download/` - Download results

### Utilities
- `POST /api/validate-aoi/` - Validate area of interest
- `GET /api/source-config-schema/{source}/` - Get source configuration schema
- `GET /api/public/exports/` - List public exports

## Authentication

Include JWT token in Authorization header:
```
Authorization: Bearer <access_token>
```

## Source Configuration

```json
{
  "google": {"confidence_threshold": 0.7},
  "microsoft": {"region": "global"}, 
  "osm": {"building_types": ["yes", "house", "apartments"]},
  "overture": {"include_height": true, "min_area": 10}
}
```

## Version Management

```bash
cz commit
cz bump
```

## Docker

```bash
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```
