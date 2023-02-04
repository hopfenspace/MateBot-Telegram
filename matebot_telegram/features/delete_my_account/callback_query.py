"""
MateBot callback query handler for the delete_my_account command
"""

import telegram

from ...base import BaseCallbackQuery, ExtendedContext


class DeleteMyAccountCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /delete_my_account
    """

    def __init__(self):
        super().__init__(
            "delete_my_account",
            "^delete_my_account",
            {
                "yes": self.handle_yes,
                "no": self.handle_no,
            }
        )

    async def handle_yes(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Continue to delete the user account of a user
        """

        _, telegram_id, core_id = data.split(" ")
        telegram_id, core_id = int(telegram_id), int(core_id)

        if update.effective_chat.type != telegram.constants.ChatType.PRIVATE:
            await update.callback_query.answer("This feature can not be used outside private chats.")
            return

        if update.callback_query.from_user.id != telegram_id:
            await update.callback_query.answer("Only the creator of this request can answer it!")
            return

        user = await context.application.client.get_core_user(update.callback_query.from_user)
        if user.id != core_id:
            await update.callback_query.answer("Only the creator of this request can answer it!")
            return

        self.logger.info(f"Attempting to delete user account {core_id} ({telegram_id})...")
        response = await context.application.client.delete_user(core_id, user)
        self.logger.info(f"The user account {core_id} has been deleted: {response}")
        context.drop_callback_data(update.callback_query)
        await update.callback_query.answer(
            "Your user account has been deleted. Any interaction with the bot may create a new account.",
            show_alert=True
        )
        await update.callback_query.message.delete()

    async def handle_no(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Abort deleting the user account
        """

        _, telegram_id, core_id = data.split(" ")
        telegram_id, core_id = int(telegram_id), int(core_id)

        if update.callback_query.from_user.id != telegram_id:
            await update.callback_query.answer("Only the creator of this request can answer it!")
            return

        user = await context.application.client.get_core_user(update.callback_query.from_user)
        if user.id != core_id:
            await update.callback_query.answer("Only the creator of this request can answer it!")
            return

        self.logger.info("The request was aborted.")
        context.drop_callback_data(update.callback_query)
        await update.callback_query.answer("Your account has not been deleted.")
        await update.callback_query.message.delete()
