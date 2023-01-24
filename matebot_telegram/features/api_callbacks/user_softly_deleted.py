"""
API callback handlers for the events USER_SOFTLY_DELETED and USER_UPDATED
"""

from matebot_sdk import schemas

from .. import _app
from ... import models


@_app.dispatcher.register_for(schemas.EventType.USER_SOFTLY_DELETED)
async def handle_user_softly_deleted(event: schemas.Event):
    user_id = int(event.data["id"])
    user = (await _app.client.get_users(id=user_id))[0]
    assert not user.active

    with _app.client.get_new_session() as session:
        user = session.query(models.TelegramUser).filter_by(user_id=user.id).get()
        if user is not None:
            telegram_id = user.telegram_id
            popped_messages = _app.client.shared_messages.pop_all_messages_by_chat(chat_id=telegram_id)
            _app.event_logger.info(f"Deleting telegram user {telegram_id} (core user {user_id}) ...")
            session.delete(user)
        registrations = session.query(models.RegistrationProcess).filter_by(telegram_id=telegram_id).all()
        for r in registrations:
            _app.event_logger.debug(f"Dropping registration process {r.id} (created: {r.created})")
            session.delete(r)
        session.commit()

    text = (
        "Your user account has been deleted. This is the last message from this bot. "
        "All data related to your user account has been deleted, too. If you want to "
        "use the bot in the future, you need to use /start to create a new user account."
    )
    await _app.bot.send_message(text, telegram_id, disable_notification=False)

    for msg in popped_messages:
        await _app.bot.edit_message_text(
            "Your user account has been deleted. Access to this message has been blocked.",
            msg.chat_id,
            msg.message_id
        )


@_app.dispatcher.register_for(schemas.EventType.USER_UPDATED)
async def handle_user_softly_deleted(event: schemas.Event):
    # TODO: Implement this in case PTB's `user_data` is used purposefully; currently unnecessary function
    pass
