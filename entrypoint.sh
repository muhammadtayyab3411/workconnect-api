#!/bin/bash

# Exit on any error
set -e

echo "🚀 Starting WorkConnect API..."

# Function to wait for database
wait_for_db() {
    echo "⏳ Waiting for database connection..."
    
    # Try to connect to database with retries
    for i in {1..30}; do
        if python -c "
import os
import psycopg2
from urllib.parse import urlparse

# Get database URL from environment
db_url = os.environ.get('DATABASE_URL')
if db_url:
    url = urlparse(db_url)
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        database=url.path[1:],
        sslmode='require'
    )
    conn.close()
    print('Database connection successful!')
else:
    # Fallback to individual env vars
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        port=os.environ.get('DB_PORT', 5432),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', ''),
        database=os.environ.get('DB_NAME', 'workconnect'),
        sslmode='require'
    )
    conn.close()
    print('Database connection successful!')
"; then
            echo "✅ Database is ready!"
            break
        else
            echo "❌ Database not ready, waiting... (attempt $i/30)"
            sleep 2
        fi
    done
}

# Wait for database
wait_for_db

# Run database migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "⚠️ Static files collection failed, continuing..."

# Create superuser if it doesn't exist
echo "👤 Creating superuser if needed..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Creating superuser...')
    User.objects.create_superuser('admin', 'admin@workconnect.com', 'admin123')
    print('✅ Superuser created successfully!')
else:
    print('✅ Superuser already exists.')
" || echo "⚠️ Superuser creation failed, continuing..."

# Start the application
echo "🌟 Starting Daphne server on port 8001..."
exec daphne -p 8001 -b 0.0.0.0 workconnect.asgi:application 