#!/bin/bash
set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME=${POSTGRES_DB:-obe_app}
DB_USER=${POSTGRES_USER:-postgres}

mkdir -p $BACKUP_DIR

echo "Creating database backup..."
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/db_backup_$DATE.sql

echo "Creating media files backup..."
docker-compose -f docker-compose.prod.yml run --rm -v $BACKUP_DIR:/backup web tar czf /backup/media_backup_$DATE.tar.gz -C /app media/

echo "Cleaning up old backups (keeping last 7 days)..."
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR"
