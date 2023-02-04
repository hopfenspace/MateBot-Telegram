"""
MateBot callback query handler for the vouch command
"""

from typing import Awaitable, Callable

import telegram
from matebot_sdk import exceptions, schemas

from ...base import BaseCallbackQuery, ExtendedContext


class VouchCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /vouch
    """

    def __init__(self):
        super().__init__(
            "vouch",
            "^vouch",
            {
                "add": self.add,
                "vouch": self.add,
                "remove": self.remove,
                "stop": self.remove
            }
        )

    @staticmethod
    async def _add(
            update: telegram.Update,
            debtor: schemas.User,
            sender: schemas.User,
            context: ExtendedContext
    ):
        """
        Handle an update to start vouching for someone
        """

        try:
            response = await context.application.client.vouch_for(debtor, sender, sender)
        except exceptions.MateBotSDKException as exc:
            await update.callback_query.message.edit_text(exc.message, reply_markup=telegram.InlineKeyboardMarkup([]))
            raise

        await update.callback_query.message.edit_text(
            f"You now vouch for {response.debtor.name} (user ID {response.debtor.id}).",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
        await update.callback_query.answer(f"You now vouch for {debtor.name}.", show_alert=True)

    @staticmethod
    async def _remove(
            update: telegram.Update,
            debtor: schemas.User,
            sender: schemas.User,
            context: ExtendedContext
    ):
        """
        Handle an update to stop vouching for someone
        """

        try:
            response = await context.application.client.vouch_stop(debtor, sender)
        except exceptions.MateBotSDKException as exc:
            await update.callback_query.message.edit_text(exc.message, reply_markup=telegram.InlineKeyboardMarkup([]))
            raise

        ext = f"No transaction was required, since {debtor.name} already had a balance of 0."
        if response.transaction is not None:
            formatted_amount = context.application.client.format_balance(response.transaction.amount)
            ext = f"A transaction of {formatted_amount} has been made."
        await update.callback_query.message.edit_text(
            f"You don't vouch for {debtor.name} anymore. Therefore, the "
            f"privileges of {debtor.name} to use this bot have been limited.\n{ext}",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
        await update.callback_query.answer(f"You don't vouch for {debtor.name} anymore.", show_alert=True)

    async def _handle_vouching(
            self,
            update: telegram.Update,
            func: Callable[[telegram.Update, schemas.User, schemas.User], Awaitable[None]],
            context: ExtendedContext,
            data: str
    ) -> None:
        """
        Handle vouching by inspecting the Update and calling appropriate functions
        """

        _, debtor_id, original_sender, option = data.split(" ")
        debtor_id = int(debtor_id)
        original_sender = int(original_sender)
        debtor = await context.application.client.get_user(debtor_id)
        sender = await context.application.client.get_core_user(update.callback_query.from_user)

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer("Only the creator of this request can answer it!")
            return

        if option == "deny":
            await update.callback_query.message.edit_text(
                "You aborted the request.",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
        elif option == "accept":
            self.logger.debug(f"Voucher change request for user {debtor.id} accepted from {sender.name}")
            await func(update, debtor, sender)
        else:
            raise ValueError(f"Invalid query data format: {data!r}")

    async def add(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle the callback query that a user wanted to start vouching
        """

        try:
            await self._handle_vouching(update, self._add, context, data)
        finally:
            context.drop_callback_data(update.callback_query)

    async def remove(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle the callback query that a user wanted to quit vouching
        """

        try:
            await self._handle_vouching(update, self._remove, context, data)
        finally:
            context.drop_callback_data(update.callback_query)
