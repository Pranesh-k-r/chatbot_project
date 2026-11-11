"""Views for Chatbot web interface and REST API endpoints."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils.html import escape

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Conversation, Message, BotConfig
from .serializers import ConversationSerializer, MessageSerializer, ChatInputSerializer
from .chatbot_service import generate_bot_response


# ==============================================================================
# Authentication & Web Page Views
# ==============================================================================

def register_view(request):
    """Handles new user registration with full validation.

    Validates password strength, confirmation, duplicate username, and duplicate email.
    """
    if request.user.is_authenticated:
        return redirect('chat')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        # Basic presence validation
        if not username or not email or not password or not password_confirm:
            messages.error(request, 'All fields are required.')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
            })

        # Username duplicate check
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, f'Username "{username}" is already taken. Please choose another.')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
            })

        # Email duplicate check
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, f'An account with email "{email}" already exists.')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
            })

        # Password confirmation check
        if password != password_confirm:
            messages.error(request, 'Passwords do not match. Please re-enter them.')
            return render(request, 'register.html', {
                'username': username,
                'email': email,
            })

        # Django password validation
        try:
            validate_password(password)
        except ValidationError as e:
            for error_msg in e.messages:
                messages.error(request, error_msg)
            return render(request, 'register.html', {
                'username': username,
                'email': email,
            })

        # Create user account
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        # Log user in directly upon successful registration
        login(request, user)
        messages.success(request, f'Welcome to Django Assistant, {user.username}! Your account was created successfully.')
        return redirect('chat')

    return render(request, 'register.html')


def login_view(request):
    """Handles user login with session-based authentication."""
    if request.user.is_authenticated:
        return redirect('chat')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Please provide both username and password.')
            return render(request, 'login.html', {'username': username})

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.GET.get('next') or 'chat'
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'login.html', {'username': username})

    return render(request, 'login.html')


def logout_view(request):
    """Logs out the user and clears session."""
    logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('login')


@login_required(login_url='login')
def chat_view(request):
    """Renders the main chatbot interface.

    Accessible to any authenticated user without needing staff/admin permissions.
    """
    conversations = Conversation.objects.filter(
        user=request.user
    ).order_by('-updated_at')

    active_bot = BotConfig.objects.filter(is_active=True).first()
    bot_name = active_bot.bot_name if active_bot else 'Django Assistant'

    context = {
        'conversations': conversations,
        'bot_name': bot_name,
        'user': request.user,
    }
    return render(request, 'chat.html', context)


# ==============================================================================
# REST API Endpoints
# ==============================================================================

class ChatAPIView(APIView):
    """POST /api/chat/

    Processes user message, creates/continues conversations, generates
    rule-based bot response, and saves both messages.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChatInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Validation Error', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_message_text = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id')

        # Locate existing conversation or initialize a new one
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id,
                    user=request.user
                )
            except Conversation.DoesNotExist:
                return Response(
                    {'error': 'Conversation not found or access denied.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Generate summary title from the first message
            title_summary = (user_message_text[:35] + '...') if len(user_message_text) > 35 else user_message_text
            conversation = Conversation.objects.create(
                user=request.user,
                title=title_summary,
                status=Conversation.STATUS_ACTIVE
            )

        # 1. Save user message
        user_message_obj = Message.objects.create(
            conversation=conversation,
            sender_type=Message.SENDER_USER,
            content=user_message_text
        )

        # 2. Generate bot response via Rule-based service
        bot_reply_text = generate_bot_response(user_message_text)

        # 3. Save bot response message
        bot_message_obj = Message.objects.create(
            conversation=conversation,
            sender_type=Message.SENDER_BOT,
            content=bot_reply_text
        )

        # Update conversation timestamp
        conversation.save()

        # Format and return JSON payload
        response_payload = {
            'status': 'success',
            'conversation_id': conversation.id,
            'conversation_title': conversation.title,
            'response': bot_reply_text,
            'bot_response': bot_reply_text,
            'user_message': MessageSerializer(user_message_obj).data,
            'bot_message': MessageSerializer(bot_message_obj).data,
        }
        return Response(response_payload, status=status.HTTP_200_OK)


class ConversationListAPIView(APIView):
    """GET /api/conversations/

    Returns all conversations belonging to the logged-in user, sorted by
    latest activity with nested messages.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        conversations = Conversation.objects.filter(
            user=request.user
        ).order_by('-updated_at')

        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConversationDetailAPIView(APIView):
    """GET /api/conversations/<int:pk>/

    Returns a single conversation and its messages belonging to the logged-in user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        conversation = get_object_or_404(
            Conversation,
            pk=pk,
            user=request.user
        )
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)
