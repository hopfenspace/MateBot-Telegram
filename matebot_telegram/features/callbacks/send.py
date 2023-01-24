"""
MateBot callback queries for the send command
"""

import telegram
from matebot_sdk.exceptions import APIException

from .base import BaseCallbackQuery
from .. import _common


class SendCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /send
    """

    def __init__(self):
        super().__init__("send", "^send", {
            "abort": self.abort,
            "confirm": self.confirm
        })

    async def confirm(self, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        Confirm and process a transaction request based on incoming callback queries
        """

        self.logger.debug("Confirming transaction")
        _, amount, original_sender, receiver_id = self.data.split(" ")
        amount = int(amount)
        original_sender = int(original_sender)
        sender = await context.application.client.get_core_user(update.callback_query.from_user)
        receiver = await context.application.client.get_user(int(receiver_id))

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer(f"Only the creator of this transaction can confirm it!")
            return

        reason = None
        for entity in update.callback_query.message.parse_entities():
            if entity.type == telegram.MessageEntity.CODE:
                if reason is None:
                    reason = update.callback_query.message.parse_entity(entity)
                else:
                    raise RuntimeError("Multiple reason definitions")

        if reason is None:
            reason = "send: <no description>"
            self.logger.error("No description provided")

        try:
            transaction = await context.application.client.create_transaction(sender, receiver, amount, reason)
            await update.callback_query.message.edit_text(
                f"Okay, you sent {context.application.client.format_balance(transaction.amount)} to {receiver.name}!",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
            await update.callback_query.answer()
        except APIException as exc:
            self.logger.warning(f"{type(exc).__name__}: {exc.message} ({exc.status}, {exc.details})")
            await update.callback_query.edit_message_text(
                f"Your request has been rejected. No money has been transferred:\n{exc.message}",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
            await update.callback_query.answer()
        finally:
            context.drop_callback_data(update.callback_query)

    async def abort(self, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        Abort a transaction request and drop the inline reply keyboard
        """

        self.logger.debug("Aborting transaction")
        _, _, original_sender, _ = self.data.split(" ")
        original_sender = int(original_sender)

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer(f"Only the creator of this transaction can abort it!")
            return

        await update.callback_query.message.edit_text(
            "You aborted the operation. No money has been sent.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
        context.drop_callback_data(update.callback_query)
