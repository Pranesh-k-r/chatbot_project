"""Django REST Framework serializers for Conversations and Messages."""

from rest_framework import serializers
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for individual Message instances."""

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender_type', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation instances including nested messages."""

    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.IntegerField(source='messages.count', read_only=True)

    class Meta:
        model = Conversation
        fields = [
            'id',
            'user',
            'title',
            'status',
            'created_at',
            'updated_at',
            'messages',
            'message_count',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'messages', 'message_count']


class ChatInputSerializer(serializers.Serializer):
    """Validates the input payload for the /api/chat/ endpoint."""

    message = serializers.CharField(
        required=True,
        max_length=2000,
        error_messages={
            'required': 'Message content is required.',
            'blank': 'Message content cannot be blank.',
            'max_length': 'Message content cannot exceed 2000 characters.'
        }
    )
    conversation_id = serializers.IntegerField(
        required=False,
        allow_null=True
    )

    def validate_message(self, value):
        stripped_value = value.strip()
        if not stripped_value:
            raise serializers.ValidationError('Message cannot be empty or only whitespace.')
        return stripped_value
