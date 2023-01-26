"""
MateBot callback query handler for the donate command
"""

import telegram.ext
from matebot_sdk.exceptions import APIException

from ..base import BaseCallbackQuery, ExtendedContext


class DonateCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /donate
    """

    def __init__(self):
        super().__init__("donate", "^donate", {
            "abort": self.abort,
            "confirm": self.confirm
        })

    async def confirm(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Confirm and process a donation requests based on incoming callback queries
        """

        self.logger.debug("Confirming donation")
        _, amount, original_sender = data.split(" ")
        amount = int(amount)
        original_sender = int(original_sender)
        sender = await context.application.client.get_core_user(update.callback_query.from_user)
        receiver = await context.application.client.community

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer(f"Only the creator of this donation can confirm it!")
            return

        try:
            transaction = await context.application.client.create_transaction(sender, receiver, amount, "donation")
            await update.callback_query.message.edit_text(
                f"Okay, you sent {context.application.client.format_balance(transaction.amount)} to the community!",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
        except APIException as exc:
            self.logger.warning(f"{type(exc).__name__}: {exc.message} ({exc.status}, {exc.details})")
            await update.callback_query.edit_message_text(
                f"Your donation has been rejected. No money has been transferred:\n{exc.message}"
            )
        finally:
            context.drop_callback_data(update.callback_query)

    async def abort(self, update: telegram.Update, context: telegram.ext.CallbackContext, data: str) -> None:
        """
        Handle the abortion of a donation requests
        """

        self.logger.debug("Cancelling donation request")
        _, _, original_sender = data.split(" ")
        original_sender = int(original_sender)

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer(f"Only the creator of this transaction can abort it!")
            return

        await update.callback_query.message.edit_text(
            "You aborted the operation. No money has been donated.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
        context.drop_callback_data(update.callback_query)
        await update.callback_query.answer()
