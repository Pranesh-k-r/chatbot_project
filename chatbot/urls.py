"""Chatbot app URL configurations."""

from django.urls import path
from . import views

urlpatterns = [
    # Web Interface
    path('', views.chat_view, name='chat'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # REST APIs
    path('api/chat/', views.ChatAPIView.as_view(), name='api_chat'),
    path('api/conversations/', views.ConversationListAPIView.as_view(), name='api_conversations'),
    path('api/conversations/<int:pk>/', views.ConversationDetailAPIView.as_view(), name='api_conversation_detail'),
]
