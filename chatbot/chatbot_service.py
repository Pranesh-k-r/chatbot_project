"""Rule-based chatbot response service.

Keeps conversation processing and response generation separate
from views and serializers.
"""

import re
from typing import Optional


def get_active_bot_name() -> str:
    """Safely retrieves the name of the currently active bot from the database.

    Falls back to 'Django Assistant' if database is unready or no active config exists.
    """
    try:
        from .models import BotConfig
        active_config = BotConfig.objects.filter(is_active=True).first()
        if active_config and active_config.bot_name:
            return active_config.bot_name
    except Exception:
        pass
    return "Django Assistant"


def generate_bot_response(user_message: str, bot_name: Optional[str] = None) -> str:
    """Generates a rule-based response based on keywords and patterns in user_message.

    Args:
        user_message: The text string submitted by the user.
        bot_name: Optional custom bot name. If not provided, queried from active BotConfig.

    Returns:
        A formatted, helpful string response.
    """
    if not bot_name:
        bot_name = get_active_bot_name()

    cleaned_text = (user_message or "").strip().lower()

    if not cleaned_text:
        return f"Hello! I am {bot_name}. Please type a message or question, and I'll be glad to help you!"

    # 1. Greetings: Hello, Hi, Hey
    if re.search(r'\b(hello|hi|hey|greetings|good\s*(morning|afternoon|evening))\b', cleaned_text):
        return (
            f"Hello there! I'm {bot_name}, your dedicated Django & Python companion. "
            "How can I assist you today? You can ask me about Python, Django, Databases, Models, or type 'help' for guidance."
        )

    # 2. How are you?
    if re.search(r'\b(how\s+are\s+you|how\s+r\s+u|how\'s\s+it\s+going|how\s+do\s+you\s+do)\b', cleaned_text):
        return (
            f"I'm functioning smoothly and ready to write code, thank you for asking! "
            f"As {bot_name}, I'm here to help you master Django web development. What are you building right now?"
        )

    # 3. Help / Capabilities
    if re.search(r'\b(help|commands?|what\s+can\s+you\s+do|topics?|assist|support)\b', cleaned_text):
        return (
            f"Here is what I can assist you with:\n"
            "• **Greetings**: Say 'Hello', 'Hi', or 'Hey'\n"
            "• **Status**: Ask 'How are you?'\n"
            "• **Python**: Learn about Python fundamentals and features\n"
            "• **Django**: Discover the Django framework architecture (MVT, ORM)\n"
            "• **Database**: Database setup, SQLite vs PostgreSQL, and migrations\n"
            "• **Models**: Creating Django models, fields, and relationships\n"
            "• **Exit**: Say 'Bye' or 'Goodbye' to wrap up the conversation"
        )

    # 4. Django
    if re.search(r'\b(django|django\s+rest\s+framework|drf|mvt)\b', cleaned_text):
        return (
            "Django is a premier high-level Python web framework that encourages rapid development and clean, "
            "pragmatic design. Key pillars include:\n"
            "1. **Batteries Included**: Built-in auth, admin panel, session management, and CSRF protection.\n"
            "2. **MVT Architecture**: Model-View-Template pattern separating business logic, data, and presentation.\n"
            "3. **Django REST Framework (DRF)**: Powerful toolkit for crafting flexible, robust Web APIs.\n"
            "4. **Security by Default**: Protection against SQL injection, XSS, CSRF, and clickjacking."
        )

    # 5. Python
    if re.search(r'\b(python|python3|pip|pep8)\b', cleaned_text):
        return (
            "Python is a versatile, high-level, interpreted programming language renowned for readable syntax "
            "and dynamic typing. It excels across web development (Django, Flask, FastAPI), data science, AI/ML, "
            "automation, and cloud infrastructure. Its zen emphasizes: 'Simple is better than complex.'"
        )

    # 6. Models / ORM
    if re.search(r'\b(models?|orm|fields?|foreignkey|manytomany)\b', cleaned_text):
        return (
            "In Django, a Model is the single, definitive source of information about your data. "
            "Each model maps to a single database table:\n"
            "• Defined by subclassing `django.db.models.Model`.\n"
            "• Field types include `CharField`, `TextField`, `IntegerField`, `DateTimeField`, etc.\n"
            "• Relationships use `ForeignKey` (one-to-many), `ManyToManyField`, and `OneToOneField`.\n"
            "• Django's ORM lets you query records in pure Python without writing raw SQL queries!"
        )

    # 7. Database
    if re.search(r'\b(database|databases|db|sqlite|sqlite3|postgres|postgresql|mysql|migration|migrations)\b', cleaned_text):
        return (
            "Django features an Object-Relational Mapper (ORM) that integrates with multiple databases:\n"
            "• **SQLite**: Default file-based database configured out of the box, ideal for development.\n"
            "• **PostgreSQL/MySQL**: Production-ready engines supported natively via database drivers.\n"
            "• **Migrations**: Managed using `python manage.py makemigrations` to package schema changes "
            "and `python manage.py migrate` to apply them safely."
        )

    # 8. Bye / Goodbye
    if re.search(r'\b(bye|goodbye|see\s+ya|see\s+you|cya|take\s+care|exit|quit)\b', cleaned_text):
        return (
            f"Goodbye! It was a pleasure chatting with you. If you need any more Django guidance, "
            f"{bot_name} is always here. Have a productive coding session!"
        )

    # 9. Fallback friendly response for unmatched input
    return (
        f"Thank you for reaching out! I didn't quite catch the specific keyword in: \"{user_message[:50]}\".\n\n"
        "As a rule-based assistant, I respond to core topics like:\n"
        "• **'Hello'** or **'How are you?'**\n"
        "• **'Python'** (language details)\n"
        "• **'Django'** (framework features & architecture)\n"
        "• **'Database'** (SQLite, PostgreSQL, migrations)\n"
        "• **'Models'** (ORM, fields, schema relationships)\n"
        "• **'Help'** (command reference) or **'Bye'** (farewell)\n\n"
        "Try asking one of these to explore further!"
    )
