from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    """Represents a chat thread between a user and the chatbot."""

    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations',
        help_text='Owner of this conversation thread.'
    )
    title = models.CharField(
        max_length=255,
        default='New Conversation',
        help_text='Title or summary of the conversation.'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        help_text='Current status of the conversation.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'

    def __str__(self):
        return f"{self.user.username} - {self.title} (#{self.id})"


class Message(models.Model):
    """Represents an individual message exchanged within a conversation."""

    SENDER_USER = 'user'
    SENDER_BOT = 'bot'
    SENDER_CHOICES = [
        (SENDER_USER, 'User'),
        (SENDER_BOT, 'Bot'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text='Conversation to which this message belongs.'
    )
    sender_type = models.CharField(
        max_length=10,
        choices=SENDER_CHOICES,
        help_text='Whether the message came from the user or the bot.'
    )
    content = models.TextField(
        help_text='The message text content.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'

    def __str__(self):
        return f"[{self.sender_type.upper()}] {self.content[:40]}"


class BotConfig(models.Model):
    """Configuration model for the chatbot instance."""

    bot_name = models.CharField(
        max_length=100,
        default='Django Assistant',
        help_text='Display name of the assistant.'
    )
    model_name = models.CharField(
        max_length=100,
        default='Rule-Based Engine v1.0',
        help_text='Underlying model or version descriptor.'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this bot config is currently active.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bot Configuration'
        verbose_name_plural = 'Bot Configurations'
        ordering = ['-created_at']

    def __str__(self):
        status_str = "Active" if self.is_active else "Inactive"
        return f"{self.bot_name} ({self.model_name}) - {status_str}"
