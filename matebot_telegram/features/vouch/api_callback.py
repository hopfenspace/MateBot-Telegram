"""
API callback handlers for the event VOUCHER_UPDATED
"""

from matebot_sdk import schemas

from .. import _app


@_app.dispatcher.register_for(schemas.EventType.VOUCHER_UPDATED)
async def handle_voucher_updated(event: schemas.Event):
    debtor_id = event.data["id"]
    voucher_id = event.data.get("voucher", None)
    transaction_id = event.data.get("transaction", None)

    voucher = voucher_id and await _app.client.get_user(voucher_id)
    transaction = transaction_id and (await _app.client.get_transactions(id=transaction_id))[0]

    debtor_telegram = _app.client.find_telegram_user(debtor_id)
    voucher_telegram = _app.client.find_telegram_user(voucher_id)

    voucher_alias = ""
    if voucher_telegram and voucher_telegram[1]:
        voucher_alias = f" alias @{voucher_telegram[1]}"
    info = ""
    if transaction:
        info = f"\nAdditionally, a payment of {_app.client.format_balance(transaction.amount)} has been made."

    if debtor_telegram is not None:
        if voucher_id is None:
            await _app.bot.send_message(
                debtor_telegram[0],
                "Your voucher has been changed. You don't have any active voucher anymore. "
                f"Therefore, some features of the bot have just been disabled for you.{info}"
            )
        elif voucher is not None:
            await _app.bot.send_message(
                debtor_telegram[0],
                f"Good news! You have a new voucher user: {voucher.name}{voucher_alias} now "
                f"vouches for you and will be held responsible for your actions. See /help for details."
            )
