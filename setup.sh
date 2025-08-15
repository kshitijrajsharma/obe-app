#!/bin/bash

set -e

echo "Setting up Building Extractor Django App..."

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is required but not installed."
    exit 1
fi

if ! command -v redis-cli &> /dev/null; then
    echo "Redis is required but not installed."
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "uv is required but not installed."
    exit 1
fi

echo "Installing dependencies..."
uv sync

if [ ! -f ".env" ]; then
    echo "Creating environment configuration..."
    cp .env.example .env
fi

DB_NAME=${POSTGRES_DB:-"obe_app"}
DB_USER=${POSTGRES_USER:-"postgres"}

echo "Setting up database..."
if ! psql -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    createdb -U "$DB_USER" "$DB_NAME"
fi

psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "Running migrations..."
mkdir -p apps/accounts/migrations apps/exports/migrations
touch apps/accounts/migrations/__init__.py
touch apps/exports/migrations/__init__.py

uv run python manage.py makemigrations accounts
uv run python manage.py makemigrations exports
uv run python manage.py migrate

echo "Collecting static files..."
uv run python manage.py collectstatic --noinput --clear

echo "Setup complete!"
echo "Create superuser: uv run python manage.py createsuperuser"
echo "Start server: uv run python manage.py runserver"
