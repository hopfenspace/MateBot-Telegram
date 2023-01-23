"""
API callback handlers for the events ALIAS_CONFIRMATION_REQUESTED and ALIAS_CONFIRMED
"""

import telegram

from matebot_sdk import schemas

from .. import _app
from ... import models, shared_messages


@_app.dispatcher.register_for(schemas.EventType.ALIAS_CONFIRMATION_REQUESTED)
async def handle_alias_confirmation_requested(event: schemas.Event):
    aliases = await _app.client.get_aliases(id=int(event.data["id"]))
    if len(aliases) != 1:
        _app.event_logger.warning(f"Confirmation request for invalid alias ID {event.data['id']}")
        return
    alias = aliases[0]
    if alias.confirmed:
        _app.event_logger.debug(f"Alias ID {alias.id} for user ID {alias.user_id} is already confirmed")
        return

    if alias.application_id == _app.client.app_id:
        _app.event_logger.debug(f"Confirmation request for origin application ID {alias.application_id} ignored")
        return
    apps = await _app.client.get_applications(id=alias.application_id)
    if len(apps) != 1:
        _app.event_logger.error(f"Not exactly one app returned for call, found {len(apps)} objects")
        return
    app = apps[0]
    username = (await _app.client.get_user(alias.user_id)).name
    user = _app.client.find_telegram_user(alias.user_id)
    if not user:
        _app.event_logger.debug("No telegram user found to notify for the newly created alias")
        return

    msg = (
        "Someone has just registered a new app alias using your existing account in another application. "
        "Currently, the other app alias is not confirmed and will therefore not be accepted for "
        "transactions or other operations.\nIf this alias was created by you, you need to ACCEPT it "
        "to connect your accounts successfully. You will then be able to use any of the confirmed "
        "registered applications interchangeably.\nIf this wasn't you, please DENY this request, "
        "which will also delete that newly created alias so it can't be activated in the future.\n\n"
        f"Application ID: {alias.application_id}\n"
        f"Application name: {app.name}\n"
        f"Creator username: {username}\n"
        f"Alias username: {alias.username}"
    )

    message = _app.bot.send_message(
        user[0],
        msg,
        reply_markup=telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("ACCEPT", callback_data=f"alias accept {alias.id} {user[0]}"),
                telegram.InlineKeyboardButton("DENY", callback_data=f"alias deny {alias.id} {user[0]}"),
            ],
            # TODO: Maybe add the report mechanic again in the future
            # [
            #     telegram.InlineKeyboardButton("DENY AND REPORT", callback_data=f"alias report {alias.id} {user[0]}"),
            # ]
        ])
    )
    _app.client.shared_messages.add_message_by(
        shared_messages.ShareType.ALIAS, alias.id, message.chat_id, message.message_id
    )


@_app.dispatcher.register_for(schemas.EventType.ALIAS_CONFIRMED)
async def handle_alias_confirmed(event: schemas.Event):
    app_name = event.data["app"]
    alias = (await _app.client.get_aliases(int(event.data["id"])))[0]
    assert alias.confirmed
    user = await _app.client.get_user(int(event.data["user"]))
    assert alias.user_id == user.id

    if alias.application_id == _app.client.app_id:
        with _app.client.get_new_session() as session:
            registrations = session.query(models.RegistrationProcess).filter_by(core_user_id=user.id).all()
            for r in registrations:
                session.delete(r)
            session.commit()

    text = (
        f"The new alias '{alias.username}' for the app '{app_name}' has been confirmed. "
        f"It is now connected to your user account. You now have a total of {len(user.aliases)} "
        f"connected aliases.\nIf this action has not been performed by you, you should disable that alias."
    )
    optional_receiver = _app.client.find_telegram_user(user.id)
    try:
        if optional_receiver is not None:
            telegram_id, _ = optional_receiver
            await _app.bot.send_message(telegram_id, text)
        for shared_msg in _app.client.shared_messages.get_messages(shared_messages.ShareType.ALIAS, alias.id):
            await _app.bot.delete_message(shared_msg.chat_id, shared_msg.message_id)
            _app.client.shared_messages.delete_message(shared_msg)
    except:
        for shared_msg in _app.client.shared_messages.get_messages(shared_messages.ShareType.ALIAS, alias.id):
            await _app.bot.edit_message_text(text, shared_msg.chat_id, shared_msg.message_id, reply_markup=None)
            _app.client.shared_messages.delete_message(shared_msg)
        raise
