from django.contrib import admin
from .models import Conversation, Message, UserPresence, MessageReadStatus


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'get_participants', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['job__title', 'participants__email', 'participants__first_name', 'participants__last_name']
    filter_horizontal = ['participants']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_participants(self, obj):
        return ', '.join([user.get_full_name() or user.email for user in obj.participants.all()[:3]])
    get_participants.short_description = 'Participants'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'message_type', 'content_preview', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'created_at']
    search_fields = ['content', 'sender__email', 'sender__first_name', 'sender__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(UserPresence)
class UserPresenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_online', 'last_seen', 'last_activity']
    list_filter = ['is_online', 'last_seen']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['last_seen', 'last_activity']


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'read_at']
    list_filter = ['read_at']
    search_fields = ['message__content', 'user__email']
    readonly_fields = ['read_at']
