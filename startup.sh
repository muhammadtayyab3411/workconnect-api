#!/bin/bash
set -e

echo "🚀 Starting WorkConnect API..."
echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

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

echo "🌟 Starting Daphne server..."
exec daphne -p 8001 -b 0.0.0.0 workconnect.asgi:application 