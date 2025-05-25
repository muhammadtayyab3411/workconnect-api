from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
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
        ).prefetch_related(
            'participants',
            'job',
            Prefetch('messages', queryset=Message.objects.order_by('-created_at')[:1])
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
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in a conversation (fallback for non-WebSocket)."""
        conversation = self.get_object()
        
        serializer = MessageCreateSerializer(
            data=request.data,
            context={'request': request, 'conversation_id': conversation.id}
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        response_serializer = MessageSerializer(message, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['patch'])
    def mark_as_read(self, request, pk=None):
        """Mark all messages in a conversation as read."""
        conversation = self.get_object()
        
        # Mark all unread messages from other users as read
        updated_count = conversation.messages.filter(
            is_read=False
        ).exclude(sender=request.user).update(is_read=True)
        
        return Response({
            'message': f'Marked {updated_count} messages as read',
            'updated_count': updated_count
        })
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search conversations by participant name or job title."""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response({'results': []})
        
        conversations = self.get_queryset().filter(
            Q(participants__first_name__icontains=query) |
            Q(participants__last_name__icontains=query) |
            Q(participants__email__icontains=query) |
            Q(job__title__icontains=query)
        ).distinct()
        
        serializer = self.get_serializer(conversations, many=True)
        return Response({'results': serializer.data})


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
