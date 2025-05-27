from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from .models import Conversation, Message, UserPresence
from .serializers import (
    ConversationListSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    UserPresenceSerializer
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get conversations where the user is a participant."""
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related(
            'job',
            'last_message',
            'last_message__sender'
        ).prefetch_related(
            'participants'
        ).distinct()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationListSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new conversation."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        
        # Return the created conversation with full details
        response_serializer = ConversationDetailSerializer(
            conversation, 
            context={'request': request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages for a specific conversation with pagination."""
        conversation = self.get_object()
        
        # Pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        offset = (page - 1) * page_size
        
        messages = conversation.messages.all().order_by('-created_at')[offset:offset + page_size]
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        
        return Response({
            'results': serializer.data,
            'page': page,
            'page_size': page_size,
            'has_more': conversation.messages.count() > offset + page_size
        })
    
    def broadcast_message(self, message, conversation):
        """Broadcast message to WebSocket consumers for real-time updates."""
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{conversation.id}'
        
        # Get avatar URL
        avatar_url = None
        if message.sender.profile_picture:
            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8001')
            avatar_url = f"{base_url}{message.sender.profile_picture.url}"
        
        # Get file URL
        file_url = None
        if message.file_attachment:
            base_url = getattr(settings, 'SITE_URL', 'http://localhost:8001')
            file_url = f"{base_url}{message.file_attachment.url}"
        
        # Broadcast to conversation participants
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'content': message.content,
                    'message_type': message.message_type,
                    'sender': {
                        'id': message.sender.id,
                        'name': message.sender.get_full_name() or message.sender.email,
                        'avatar': avatar_url,
                        'role': message.sender.role
                    },
                    'file_url': file_url,
                    'is_read': message.is_read,
                    'created_at': message.created_at.isoformat(),
                    'updated_at': message.updated_at.isoformat()
                }
            }
        )
        
        # Send global notifications to participants (except sender)
        participants = conversation.participants.exclude(id=message.sender.id)
        sender_name = message.sender.get_full_name() or message.sender.email
        
        for participant in participants:
            async_to_sync(channel_layer.group_send)(
                f'notifications_{participant.id}',
                {
                    'type': 'new_message_notification',
                    'conversation_id': str(conversation.id),
                    'message': {
                        'id': str(message.id),
                        'content': message.content,
                        'sender_name': sender_name,
                        'created_at': message.created_at.isoformat()
                    },
                    'sender_name': sender_name
                }
            )

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a conversation (fallback for non-WebSocket)."""
        conversation = self.get_object()
        
        # Combine request.data and request.FILES for proper file handling
        data = request.data.copy()
        if request.FILES:
            data.update(request.FILES)
        
        serializer = MessageCreateSerializer(
            data=data,
            context={'request': request, 'conversation_id': conversation.id}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        # Broadcast message to WebSocket consumers for real-time updates
        self.broadcast_message(message, conversation)
        
        response_serializer = MessageSerializer(message, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Mark messages as read in a conversation."""
        conversation = self.get_object()
        message_ids = request.data.get('message_ids', [])
        
        if message_ids:
            # Mark specific messages as read
            updated_count = conversation.messages.filter(
                id__in=message_ids
            ).exclude(sender=request.user).update(is_read=True)
        else:
            # Mark all unread messages as read
            updated_count = conversation.messages.filter(
                is_read=False
            ).exclude(sender=request.user).update(is_read=True)
        
        return Response({
            'message': f'{updated_count} messages marked as read',
            'updated_count': updated_count
        })


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for reading messages (messages are created via WebSocket or conversation endpoint).
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        """Get messages from conversations where the user is a participant."""
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related('sender', 'conversation')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search messages by content."""
        query = request.query_params.get('q', '').strip()
        conversation_id = request.query_params.get('conversation_id')
        
        if not query:
            return Response({'results': []})
        
        messages = self.get_queryset().filter(content__icontains=query)
        
        if conversation_id:
            messages = messages.filter(conversation_id=conversation_id)
        
        messages = messages.order_by('-created_at')[:50]
        serializer = self.get_serializer(messages, many=True)
        return Response({'results': serializer.data})


class UserPresenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for checking user presence status.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserPresenceSerializer
    
    def get_queryset(self):
        """Get presence status for users in the same conversations."""
        user_conversations = Conversation.objects.filter(participants=self.request.user)
        participant_ids = user_conversations.values_list('participants', flat=True).distinct()
        
        return UserPresence.objects.filter(
            user_id__in=participant_ids
        ).select_related('user')
    
    @action(detail=False, methods=['get'])
    def online_users(self, request):
        """Get list of currently online users."""
        online_users = self.get_queryset().filter(is_online=True)
        serializer = self.get_serializer(online_users, many=True)
        return Response({'results': serializer.data})
