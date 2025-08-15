# Building Extractor Django App

Django application for extracting building footprints from multiple data sources using the Open Building Extractor (OBE) library.

## Features

- Multiple data sources: Google Open Buildings, Microsoft Building Footprints, OpenStreetMap, Overture Buildings
- Interactive map interface with MapLibre GL JS
- Background processing with Huey + Redis
- Multiple output formats: GeoParquet, GeoJSON, Shapefile, GeoPackage
- Public sharing for exports
- Modern UI with HTMX, Alpine.js, and Tailwind CSS

## Tech Stack

- Backend: Django 5.0+ with PostGIS
- Queue: Huey + Redis
- Frontend: Django Templates + HTMX + Alpine.js + Tailwind CSS
- Maps: MapLibre GL JS
- Authentication: Django-Allauth with OAuth2
- Database: PostgreSQL + PostGIS

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL with PostGIS
- Redis server
- GDAL/GEOS libraries
- uv package manager

### Setup

```bash
git clone <your-repo>
cd obe-app
./setup.sh
```

### Run

```bash
uv run python manage.py createsuperuser
uv run python manage.py runserver

# In separate terminal:
uv run python manage.py run_huey
```

Visit http://localhost:8000

## Docker Setup

```bash
docker-compose up --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Usage

1. Sign up/Login
2. Create new export
3. Draw area of interest on map
4. Select data source and output format
5. Run export (processes in background)
6. Download results when complete

## Data Sources

- **Google Open Buildings**: Global building footprints with confidence scores
- **Microsoft Building Footprints**: Regional datasets (US, Canada, etc.)
- **OpenStreetMap**: Community-contributed building data
- **Overture Buildings**: Overture Maps Foundation dataset

Data source settings:

```python
# Google Buildings
{"confidence_threshold": 0.7}

# Microsoft Buildings
{"region": "global"}

# OSM Buildings
{"building_types": ["yes", "house", "apartments"]}

# Overture Buildings
{"include_height": True, "min_area": 10}
```

## API Endpoints

- `GET /api/exports/` - List exports
- `POST /api/exports/` - Create export
- `GET /api/exports/{id}/` - Export details
- `POST /api/validate-aoi/` - Validate area of interest

## Development

### Package Management

```bash
uv add package-name
uv sync
uv run python manage.py command
```

### Troubleshooting

**Migration Issues:**
- Ensure DATABASE_URL uses `postgis://` protocol
- Verify migration order: accounts before exports
- Check database connection: `uv run python manage.py check --database default`

**Common Errors:**
- `'DatabaseOperations' object has no attribute 'geo_db_type'` → Use `postgis://` URL
- Foreign key constraint errors → Run accounts migrations first

### Quick Reference

```bash
uv run python manage.py showmigrations
uv run python manage.py makemigrations accounts
uv run python manage.py makemigrations exports
uv run python manage.py migrate accounts
uv run python manage.py migrate exports
uv run python manage.py check --database default
uv run python manage.py dbshell --command="SELECT PostGIS_Version();"

rm -rf apps/*/migrations/
mkdir -p apps/accounts/migrations apps/exports/migrations
touch apps/accounts/migrations/__init__.py
touch apps/exports/migrations/__init__.py
```

## License

MIT License
