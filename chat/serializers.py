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
            # Get the request from context to build absolute URL
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None

class MessageSerializer(serializers.ModelSerializer):
    sender = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = ["id", "content", "sender", "created_at"]

class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["content", "message_type"]
    
    def create(self, validated_data):
        request = self.context['request']
        conversation_id = self.context['conversation_id']
        
        message = Message.objects.create(
            conversation_id=conversation_id,
            sender=request.user,
            **validated_data
        )
        return message

class ConversationListSerializer(serializers.ModelSerializer):
    participants = UserBasicSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    job_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ["id", "participants", "job", "job_title", "last_message", "unread_count", "created_at", "updated_at"]
    
    def get_unread_count(self, obj):
        user = self.context.get("request").user
        if user:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0
    
    def get_job_title(self, obj):
        return obj.job.title if obj.job else None

class ConversationDetailSerializer(serializers.ModelSerializer):
    participants = UserBasicSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    job_title = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = ["id", "participants", "job", "job_title", "messages", "created_at", "updated_at"]
    
    def get_job_title(self, obj):
        return obj.job.title if obj.job else None

class ConversationCreateSerializer(serializers.ModelSerializer):
    participant_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    
    class Meta:
        model = Conversation
        fields = ["job", "participant_ids"]
    
    def create(self, validated_data):
        participant_ids = validated_data.pop("participant_ids")
        conversation = Conversation.objects.create(**validated_data)
        participants = User.objects.filter(id__in=participant_ids)
        conversation.participants.set(participants)
        creator = self.context["request"].user
        if creator not in conversation.participants.all():
            conversation.participants.add(creator)
        return conversation

class UserPresenceSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = UserPresence
        fields = ["user", "is_online", "last_seen"]
