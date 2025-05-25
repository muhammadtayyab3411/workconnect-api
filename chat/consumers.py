import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from .models import Conversation, Message, UserPresence

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling chat messages in a specific conversation.
    """
    
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if user is participant in the conversation
        if not await self.is_participant():
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user presence
        await self.update_user_presence(True)
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Update user presence
        if hasattr(self, 'user') and self.user.is_authenticated:
            await self.update_user_presence(False)
    
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'send_message':
                await self.handle_send_message(text_data_json)
            elif message_type == 'mark_as_read':
                await self.handle_mark_as_read(text_data_json)
            elif message_type == 'typing_start':
                await self.handle_typing_indicator(text_data_json, True)
            elif message_type == 'typing_stop':
                await self.handle_typing_indicator(text_data_json, False)
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_send_message(self, data):
        content = data.get('content', '').strip()
        message_type = data.get('message_type', 'text')
        
        if not content and message_type == 'text':
            return
        
        # Save message to database
        message = await self.save_message(content, message_type)
        
        if message:
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': str(message.id),
                        'content': message.content,
                        'message_type': message.message_type,
                        'sender': {
                            'id': message.sender.id,
                            'name': message.sender.get_full_name() or message.sender.email,
                            'avatar': message.sender.profile_picture.url if message.sender.profile_picture else None
                        },
                        'created_at': message.created_at.isoformat(),
                        'is_read': message.is_read
                    }
                }
            )
    
    async def handle_mark_as_read(self, data):
        message_ids = data.get('message_ids', [])
        await self.mark_messages_as_read(message_ids)
        
        # Notify other participants
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'messages_read',
                'message_ids': message_ids,
                'reader_id': self.user.id
            }
        )
    
    async def handle_typing_indicator(self, data, is_typing):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'user_name': self.user.get_full_name() or self.user.email,
                'is_typing': is_typing
            }
        )
    
    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'message_received',
            'message': message
        }))
    
    async def messages_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'message_ids': event['message_ids'],
            'reader_id': event['reader_id']
        }))
    
    async def typing_indicator(self, event):
        # Don't send typing indicator to the sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing_indicator',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_typing': event['is_typing']
            }))
    
    @database_sync_to_async
    def is_participant(self):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except (Conversation.DoesNotExist, ValueError):
            return False
    
    @database_sync_to_async
    def save_message(self, content, message_type):
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                message_type=message_type
            )
            return message
        except Conversation.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_messages_as_read(self, message_ids):
        Message.objects.filter(
            id__in=message_ids,
            conversation_id=self.conversation_id
        ).exclude(sender=self.user).update(is_read=True)
    
    @database_sync_to_async
    def update_user_presence(self, is_online):
        presence, created = UserPresence.objects.get_or_create(
            user=self.user,
            defaults={'is_online': is_online}
        )
        if not created:
            presence.is_online = is_online
            presence.save()


class PresenceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for handling user presence (online/offline status).
    """
    
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.room_group_name = 'presence'
        
        # Join presence group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Update user presence to online
        await self.update_user_presence(True)
        
        # Notify others that user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_change',
                'user_id': self.user.id,
                'user_name': self.user.get_full_name() or self.user.email,
                'is_online': True
            }
        )
    
    async def disconnect(self, close_code):
        # Leave presence group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Update user presence to offline
        await self.update_user_presence(False)
        
        # Notify others that user is offline
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status_change',
                'user_id': self.user.id,
                'user_name': self.user.get_full_name() or self.user.email,
                'is_online': False
            }
        )
    
    async def user_status_change(self, event):
        # Don't send status change to the user themselves
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_status_change',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'is_online': event['is_online']
            }))
    
    @database_sync_to_async
    def update_user_presence(self, is_online):
        presence, created = UserPresence.objects.get_or_create(
            user=self.user,
            defaults={'is_online': is_online}
        )
        if not created:
            presence.is_online = is_online
            presence.save() 