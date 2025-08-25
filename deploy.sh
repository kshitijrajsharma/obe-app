#!/bin/bash
set -e

echo "Starting production deployment..."

if [ ! -f ".env.prod" ]; then
    echo "Error: .env.prod file not found. Copy .env.prod.example and configure it."
    exit 1
fi

echo "Pulling latest images..."
docker-compose -f docker-compose.prod.yml pull

echo "Running migrations..."
docker-compose -f docker-compose.prod.yml run --rm web python manage.py migrate

echo "Collecting static files..."
docker-compose -f docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput

echo "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

echo "Deployment complete!"
echo "Health check: curl http://localhost:8000/health/"
