"""
ASGI config for workconnect project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workconnect.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Run migrations automatically when Django starts
try:
    print("🚀 Running migrations automatically...")
    from django.core.management import execute_from_command_line
    execute_from_command_line(['manage.py', 'migrate', '--noinput'])
    print("✅ Migrations completed successfully!")
    
    # Create superuser if needed
    print("👤 Creating superuser if needed...")
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(is_superuser=True).exists():
        print('Creating superuser...')
        User.objects.create_superuser('admin', 'admin@workconnect.com', 'admin123')
        print('✅ Superuser created successfully!')
    else:
        print('✅ Superuser already exists.')
except Exception as e:
    print(f"⚠️ Migration or superuser creation failed: {e}")
    print("Continuing with application startup...")

# Import routing and middleware after Django is set up
from chat import routing
from chat.middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns
        )
    ),
})
