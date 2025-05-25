from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet, basename='documents')
router.register(r'jobs', views.JobViewSet, basename='jobs')
router.register(r'job-categories', views.JobCategoryViewSet, basename='job-categories')
router.register(r'bids', views.BidViewSet, basename='bids')

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.AuthViewSet.as_view(), {'action': 'register'}, name='register'),
    path('auth/login/', views.AuthViewSet.as_view(), {'action': 'login'}, name='login'),
    path('auth/refresh/', views.AuthViewSet.as_view(), {'action': 'refresh'}, name='refresh'),
    path('auth/logout/', views.AuthViewSet.as_view(), {'action': 'logout'}, name='logout'),
    
    # Profile endpoints
    path('auth/profile/', views.ProfileView.as_view(), name='profile'),
    path('auth/profile/picture/', views.ProfilePictureUploadView.as_view(), name='profile-picture'),
    
    # Workers endpoint
    path('workers/', views.WorkersListView.as_view(), name='workers-list'),
    path('workers/<int:worker_id>/', views.WorkerDetailView.as_view(), name='worker-detail'),
    
    # Include router URLs first
    path('', include(router.urls)),
] 