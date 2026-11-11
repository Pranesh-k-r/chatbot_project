"""Automated test suite for the Django Assistant application."""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status

from .models import Conversation, Message, BotConfig
from .chatbot_service import generate_bot_response


class AuthenticationAndPageTests(TestCase):
    """Tests for authentication pages and view protection."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )

    def test_login_protection_redirects_anonymous_user(self):
        """Unauthenticated user accessing chat page must be redirected to login."""
        response = self.client.get(reverse('chat'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_authenticated_user_can_access_chat_page(self):
        """Normal authenticated user can access chat page without staff/admin permissions."""
        self.client.login(username='testuser', password='Password123!')
        response = self.client.get(reverse('chat'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat.html')
        self.assertContains(response, 'testuser')

    def test_user_registration_success(self):
        """Valid registration creates account and logs user in."""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_user_registration_duplicate_username(self):
        """Duplicate username registration is rejected."""
        response = self.client.post(reverse('register'), {
            'username': 'testuser',
            'email': 'other@example.com',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already taken')

    def test_user_registration_password_mismatch(self):
        """Mismatched passwords during registration are rejected."""
        response = self.client.post(reverse('register'), {
            'username': 'mismatchuser',
            'email': 'mismatch@example.com',
            'password': 'Password123!',
            'password_confirm': 'DifferentPassword123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')

    def test_user_logout(self):
        """Logout ends user session and redirects to login."""
        self.client.login(username='testuser', password='Password123!')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)


class ChatAPITests(TestCase):
    """Tests for DRF API endpoints."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='Password123!'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='Password123!'
        )
        self.client.login(username='alice', password='Password123!')

    def test_unauthenticated_api_access_blocked(self):
        """Unauthenticated requests to /api/chat/ are rejected with 403."""
        self.client.logout()
        response = self.client.post(reverse('api_chat'), {'message': 'Hello'}, content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_send_valid_message_creates_conversation_and_messages(self):
        """Sending a valid message creates a new conversation, user msg, and bot msg."""
        payload = {'message': 'Hello Django'}
        response = self.client.post(
            reverse('api_chat'),
            payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('conversation_id', data)
        self.assertIn('response', data)
        self.assertEqual(data['status'], 'success')

        # Verify database records
        conversation = Conversation.objects.get(id=data['conversation_id'])
        self.assertEqual(conversation.user, self.user1)
        messages = conversation.messages.all()
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages[0].sender_type, 'user')
        self.assertEqual(messages[0].content, 'Hello Django')
        self.assertEqual(messages[1].sender_type, 'bot')

    def test_continue_existing_conversation(self):
        """Supplying conversation_id appends messages to that conversation."""
        conversation = Conversation.objects.create(
            user=self.user1,
            title='Alice Thread'
        )
        payload = {
            'conversation_id': conversation.id,
            'message': 'Tell me about models'
        }
        response = self.client.post(
            reverse('api_chat'),
            payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['conversation_id'], conversation.id)
        self.assertEqual(conversation.messages.count(), 2)

    def test_reject_empty_message(self):
        """Empty or whitespace-only messages are rejected with 400 Bad Request."""
        for empty_msg in ['', '   ', ' \t \n ']:
            response = self.client.post(
                reverse('api_chat'),
                {'message': empty_msg},
                content_type='application/json'
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_message_exceeding_character_limit(self):
        """Messages longer than 2000 characters are rejected with 400 Bad Request."""
        oversized = 'a' * 2001
        response = self.client.post(
            reverse('api_chat'),
            {'message': oversized},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prevent_access_to_other_users_conversation(self):
        """User cannot send a message into another user's conversation."""
        bobs_conversation = Conversation.objects.create(
            user=self.user2,
            title="Bob's Secret Conversation"
        )
        # Alice tries to post to Bob's conversation
        response = self.client.post(
            reverse('api_chat'),
            {
                'conversation_id': bobs_conversation.id,
                'message': 'Sneaking into Bob thread'
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Bob's conversation must remain untouched
        self.assertEqual(bobs_conversation.messages.count(), 0)

    def test_conversations_api_returns_only_own_conversations(self):
        """GET /api/conversations/ returns conversations of logged-in user only."""
        Conversation.objects.create(user=self.user1, title='Alice convo 1')
        Conversation.objects.create(user=self.user1, title='Alice convo 2')
        Conversation.objects.create(user=self.user2, title='Bob private convo')

        response = self.client.get(reverse('api_conversations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 2)
        titles = [item['title'] for item in data]
        self.assertIn('Alice convo 1', titles)
        self.assertIn('Alice convo 2', titles)
        self.assertNotIn('Bob private convo', titles)


class RuleBasedChatbotServiceTests(TestCase):
    """Tests for chatbot_service.py logic."""

    def test_greetings_keyword(self):
        reply = generate_bot_response("Hello there!")
        self.assertIn("Hello there!", reply)

    def test_how_are_you_keyword(self):
        reply = generate_bot_response("How are you?")
        self.assertIn("functioning smoothly", reply)

    def test_python_keyword(self):
        reply = generate_bot_response("Tell me about Python")
        self.assertIn("programming language", reply)

    def test_django_keyword(self):
        reply = generate_bot_response("What is Django?")
        self.assertIn("web framework", reply)

    def test_database_keyword(self):
        reply = generate_bot_response("How does the database work?")
        self.assertIn("SQLite", reply)

    def test_models_keyword(self):
        reply = generate_bot_response("Explain Django models")
        self.assertIn("Model", reply)

    def test_help_keyword(self):
        reply = generate_bot_response("help please")
        self.assertIn("Here is what I can assist you with", reply)

    def test_bye_keyword(self):
        reply = generate_bot_response("Bye for now")
        self.assertIn("Goodbye", reply)

    def test_fallback_unmatched_keyword(self):
        reply = generate_bot_response("quantum mechanics in astrophysics")
        self.assertIn("didn't quite catch", reply)
