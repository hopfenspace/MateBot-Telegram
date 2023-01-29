"""
API callback handler for the event TRANSACTION_CREATED
"""

import telegram

from matebot_sdk import schemas

from .. import _app


@_app.dispatcher.register_for(schemas.EventType.TRANSACTION_CREATED)
async def handle_incoming_transaction_created_notification(event: schemas.Event):
    transaction = (await _app.client.get_transactions(id=int(event.data["id"])))[0]
    sender_user = _app.client.find_telegram_user(transaction.sender.id)
    receiver_user = _app.client.find_telegram_user(transaction.receiver.id)

    community = await _app.client.community
    if transaction.sender.id == community.id:
        alias = ""
        if receiver_user and receiver_user[1]:
            alias = f" alias @{receiver_user[1]}"
        msg = f"*Incoming transaction*\nThe community has sent {_app.client.format_balance(transaction.amount)} " \
              f"to the user {transaction.receiver.name}{alias}.\nDescription: `{transaction.reason}`"
        for notification_receiver in _app.config.chats.transactions:
            await _app.bot.send_message(notification_receiver, msg, parse_mode=telegram.constants.ParseMode.MARKDOWN)

    if transaction.receiver.id == community.id:
        alias = ""
        if receiver_user and receiver_user[1]:
            alias = f" alias @{receiver_user[1]}"
        msg = f"*Incoming transaction*\nThe user {transaction.sender.name}{alias} " \
              f"has sent {_app.client.format_balance(transaction.amount)} to the " \
              f"community.\nDescription: `{transaction.reason}`"
        for notification_receiver in _app.config.chats.transactions:
            await _app.bot.send_message(notification_receiver, msg, parse_mode=telegram.constants.ParseMode.MARKDOWN)

    if [a for a in transaction.receiver.aliases if a.confirmed and a.application_id == _app.client.app_id]:
        if receiver_user:
            alias = ""
            if sender_user and sender_user[1]:
                alias = f" alias @{sender_user[1]}"
            msg = f"Good news! You received a payment of {_app.client.format_balance(transaction.amount)} " \
                  f"from {transaction.sender.name}{alias}.\nDescription: `{transaction.reason}`"
            await _app.bot.send_message(receiver_user[0], msg, parse_mode=telegram.constants.ParseMode.MARKDOWN)
