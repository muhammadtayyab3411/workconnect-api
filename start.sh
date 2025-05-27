#!/bin/bash

# Exit on any error
set -e

echo "Starting WorkConnect API..."

# Wait for database to be ready
echo "Waiting for database..."
python manage.py wait_for_db || echo "wait_for_db command not found, continuing..."

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "Static files collection failed, continuing..."

# Create superuser if it doesn't exist (optional)
echo "Creating superuser if needed..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Creating superuser...')
    User.objects.create_superuser('admin', 'admin@workconnect.com', 'admin123')
    print('Superuser created successfully!')
else:
    print('Superuser already exists.')
" || echo "Superuser creation failed, continuing..."

# Start the application
echo "Starting Daphne server..."
exec daphne -p 8001 -b 0.0.0.0 workconnect.asgi:application 