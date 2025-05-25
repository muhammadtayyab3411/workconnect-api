from django.urls import path, include
from . import views

urlpatterns = [
    # API endpoints will be added here as we build them
    path('health/', views.health_check, name='health_check'),
    path('', include('users.urls')),
] 