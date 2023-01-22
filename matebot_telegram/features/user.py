"""
API callback handler collection for internal purposes only
"""

import logging

from matebot_sdk import schemas

from .. import client, persistence
from ..api_callback import dispatcher


@dispatcher.register_for(schemas.EventType.USER_SOFTLY_DELETED)
async def _handle_user_softly_deleted(event: schemas.Event):
    user_id = int(event.data["id"])
    user = (await client.client.get_users(id=user_id))[0]
    assert not user.active

    with client.client.get_new_session() as session:
        user = session.query(persistence.TelegramUser).filter_by(user_id=user.id).get()
        telegram_id = user.telegram_id
        popped_messages = client.client.shared_messages.pop_all_messages_by_chat(chat_id=telegram_id)
        logging.getLogger("api-callback").info(f"Deleting telegram user {telegram_id} (core user {user_id}) ...")
        session.delete(user)
        session.query(persistence.RegistrationProcess).filter_by()
        session.commit()

    text = (
        "Your user account has been deleted. This is the last message from this bot. "
        "All data related to your user account has been deleted, too. If you want to "
        "use the bot in the future, you need to use /start to create a new user account."
    )
    client.client.bot.send_message(text, telegram_id, disable_notification=False)

    for msg in popped_messages:
        client.client.bot.edit_message_text(
            "Your user account has been deleted. Access to this message has been blocked.",
            msg.chat_id,
            msg.message_id
        )
