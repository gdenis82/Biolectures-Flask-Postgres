#!/bin/bash
set -e

# Wait for the database to be ready
echo "Waiting for database to be ready..."

while ! nc -z db 5432; do
  sleep 2
done

echo "Database started"

# Check if migrations directory exists
if [ ! -d "migrations" ]; then
  echo "Initializing migrations directory..."
  flask db init
else
  echo "Migrations directory already exists, skipping initialization..."
fi

# Create and apply migrations
echo "Creating migrations..."
flask db migrate -m "Auto-migration"
echo "Applying migrations..."
flask db upgrade

# Initialize database with required data
echo "Initializing database with required data..."
# python add_auth_menu_items.py

# Start the application
echo "Starting application..."
exec gunicorn --bind 0.0.0.0:5000 wsgi:app
