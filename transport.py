"""Transport layer — swap between Telegram and WhatsApp at startup.

All of server.py imports handler functions from here instead of directly
from telegram_handler. Set TRANSPORT=whatsapp in .env to use WhatsApp.
"""

import os

_TRANSPORT = os.environ.get("TRANSPORT", "telegram").lower()

if _TRANSPORT == "whatsapp":
    from whatsapp_handler import (
        answer_callback_query,
        close_client,
        delete_message,
        delete_webhook,
        download_document,
        download_photo,
        get_updates,
        register_bot_commands,
        register_webhook,
        send_chat_action,
        send_inline_keyboard,
        send_message,
        send_photo,
        send_video,
        send_voice,
    )
else:
    from telegram_handler import (  # noqa: F401
        answer_callback_query,
        close_client,
        delete_message,
        delete_webhook,
        download_document,
        download_photo,
        get_updates,
        register_bot_commands,
        register_webhook,
        send_chat_action,
        send_inline_keyboard,
        send_message,
        send_photo,
        send_video,
        send_voice,
    )
