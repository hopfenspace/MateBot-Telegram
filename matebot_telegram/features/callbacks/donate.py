"""
MateBot command executor classes for /donate and its callback queries
"""

import telegram.ext
from matebot_sdk.exceptions import APIException

from .base import BaseCallbackQuery


class DonateCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /donate
    """

    def __init__(self):
        super().__init__("donate", "^donate", {
            "test": self.fix,
            "yes": self.fix,
            "no": self.drop,
            "maybe": self.fix,
            "abort": self.abort,
            "confirm": self.confirm
        })

    async def fix(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        print("fix", update, self)

    async def drop(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        print("drop it")
        await update.callback_query.message.edit_text("no!")
        print("x", context.drop_callback_data(update.callback_query))

    async def confirm(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        Confirm and process a donation requests based on incoming callback queries

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        self.logger.debug("Confirming donation")
        _, amount, original_sender = self.data.split(" ")
        amount = int(amount)
        original_sender = int(original_sender)
        sender = await self.client.get_core_user(update.callback_query.from_user)
        receiver = await self.client.community

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer(f"Only the creator of this donation can confirm it!")
            return

        try:
            transaction = await self.client.create_transaction(sender, receiver, amount, "donation")
            await update.callback_query.message.edit_text(
                f"Okay, you sent {self.client.format_balance(transaction.amount)} to the community!",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
        except APIException as exc:
            self.logger.warning(f"{type(exc).__name__}: {exc.message} ({exc.status}, {exc.details})")
            await update.callback_query.edit_message_text(
                f"Your donation has been rejected. No money has been transferred:\n{exc.message}"
            )

    async def abort(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        Abort a donation requests

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        self.logger.debug("Aborting donation")
        _, _, original_sender = self.data.split(" ")
        original_sender = int(original_sender)

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer(f"Only the creator of this transaction can abort it!")
            return

        await update.callback_query.message.edit_text(
            "You aborted the operation. No money has been donated.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
