from django.db import models
from django.contrib.auth import get_user_model
from users.models import Job
import uuid

User = get_user_model()


class Conversation(models.Model):
    """
    Represents a conversation between users, optionally related to a job.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(User, related_name='conversations')
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message = models.ForeignKey('Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        participant_names = ', '.join([user.get_full_name() or user.email for user in self.participants.all()[:2]])
        if self.job:
            return f"Conversation about {self.job.title} - {participant_names}"
        return f"Conversation - {participant_names}"
    
    @property
    def unread_count(self):
        """Get total unread messages in this conversation"""
        return self.messages.filter(is_read=False).count()


class Message(models.Model):
    """
    Represents a message in a conversation.
    """
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('voice', 'Voice'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')
    file_attachment = models.FileField(upload_to='chat_files/%Y/%m/%d/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.get_full_name() or self.sender.email} at {self.created_at}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update conversation's last_message and updated_at
        if is_new:
            self.conversation.last_message = self
            self.conversation.save(update_fields=['last_message', 'updated_at'])


class UserPresence(models.Model):
    """
    Tracks user online/offline status and last activity.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='presence')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        status = "Online" if self.is_online else f"Last seen {self.last_seen}"
        return f"{self.user.get_full_name() or self.user.email} - {status}"


class MessageReadStatus(models.Model):
    """
    Tracks which messages have been read by which users.
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_read_statuses')
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['message', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.email} read message at {self.read_at}"
