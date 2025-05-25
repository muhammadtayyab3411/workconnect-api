from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<conversation_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/presence/$', consumers.PresenceConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.GlobalNotificationsConsumer.as_asgi()),
] 