from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, UserPresence, MessageReadStatus

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information for chat contexts."""
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'name', 'avatar', 'role']
    
    def get_name(self, obj):
        return obj.get_full_name() or obj.email
    
    def get_avatar(self, obj):
        if obj.profile_picture:
            return obj.profile_picture.url
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    sender = UserBasicSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'content', 'message_type', 'sender', 'file_url',
            'is_read', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']
    
    def get_file_url(self, obj):
        if obj.file_attachment:
            return obj.file_attachment.url
        return None


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for listing conversations."""
    participants = UserBasicSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'job', 'job_title', 'last_message',
            'unread_count', 'created_at', 'updated_at'
        ]
    
    def get_unread_count(self, obj):
        user = self.context.get('request').user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()
    
    def get_job_title(self, obj):
        return obj.job.title if obj.job else None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer for conversation details with messages."""
    participants = UserBasicSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'job', 'job_title', 'messages',
            'created_at', 'updated_at'
        ]
    
    def get_messages(self, obj):
        # Get paginated messages (latest 50 by default)
        messages = obj.messages.all().order_by('-created_at')[:50]
        return MessageSerializer(messages, many=True, context=self.context).data
    
    def get_job_title(self, obj):
        return obj.job.title if obj.job else None


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new conversations."""
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )
    
    class Meta:
        model = Conversation
        fields = ['job', 'participant_ids']
    
    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        conversation = Conversation.objects.create(**validated_data)
        
        # Add participants
        participants = User.objects.filter(id__in=participant_ids)
        conversation.participants.set(participants)
        
        # Add the creator as a participant if not already included
        creator = self.context['request'].user
        if creator not in conversation.participants.all():
            conversation.participants.add(creator)
        
        return conversation


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new messages."""
    
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'file_attachment']
    
    def create(self, validated_data):
        conversation_id = self.context['conversation_id']
        sender = self.context['request'].user
        
        conversation = Conversation.objects.get(id=conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            **validated_data
        )
        return message


class UserPresenceSerializer(serializers.ModelSerializer):
    """Serializer for user presence status."""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = UserPresence
        fields = ['user', 'is_online', 'last_seen', 'last_activity'] 