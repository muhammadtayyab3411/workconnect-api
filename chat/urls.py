from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet, UserPresenceViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'presence', UserPresenceViewSet, basename='presence')

urlpatterns = [
    path('api/chat/', include(router.urls)),
] 