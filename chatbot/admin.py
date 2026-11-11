"""Django Admin configuration for Conversation, Message, and BotConfig."""

from django.contrib import admin
from .models import Conversation, Message, BotConfig


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('title', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender_type', 'short_content', 'created_at')
    list_filter = ('sender_type', 'created_at')
    search_fields = ('content', 'conversation__title', 'conversation__user__username')
    readonly_fields = ('created_at',)
    list_per_page = 50

    def short_content(self, obj):
        return obj.content[:60] + ('...' if len(obj.content) > 60 else '')
    short_content.short_description = 'Content Preview'


@admin.register(BotConfig)
class BotConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'bot_name', 'model_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('bot_name', 'model_name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at',)
