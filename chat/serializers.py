from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
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
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_attachment.url)
            return obj.file_attachment.url
        return None

class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new messages."""
    
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'file_attachment']
    
    def validate_file_attachment(self, value):
        """Validate file upload with size and type restrictions."""
        if value:
            # File size validation (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB in bytes
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"File size too large. Maximum size is {max_size // (1024 * 1024)}MB."
                )
            
            # File type validation
            allowed_types = [
                # Images
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                # Documents
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                # Text files
                'text/plain', 'text/csv',
                # Archives
                'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed'
            ]
            
            if hasattr(value, 'content_type') and value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Invalid file type. Allowed types: images, PDF, Word, Excel, PowerPoint, text files, and archives."
                )
        
        return value
    
    def validate(self, data):
        """Validate that either content or file is provided."""
        content = data.get('content', '').strip()
        file_attachment = data.get('file_attachment')
        message_type = data.get('message_type', 'text')
        
        # For text messages, content is required
        if message_type == 'text' and not content:
            raise serializers.ValidationError("Content is required for text messages.")
        
        # For file messages, file is required
        if message_type == 'file' and not file_attachment:
            raise serializers.ValidationError("File attachment is required for file messages.")
        
        # Auto-detect message type based on file
        if file_attachment and message_type == 'text':
            if hasattr(file_attachment, 'content_type'):
                if file_attachment.content_type.startswith('image/'):
                    data['message_type'] = 'image'
                else:
                    data['message_type'] = 'file'
        
        return data
    
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
