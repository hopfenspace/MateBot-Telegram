"""
MateBot command executor class for /delete_my_account
"""

import telegram.ext

from ...base import BaseCommand, err, ExtendedContext, Namespace


class DeleteMyAccountCommand(BaseCommand):
    """
    Command executor for /delete_my_account
    """

    def __init__(self):
        super().__init__(
            "delete_my_account",
            "Ask to delete your MateBot user account\n\n"
            "This command allows you to _permanently_ remove your MateBot "
            "account. Important: This does *not only* remove this application, "
            "*but also* every other of your applications, balance, name and "
            "other user-related data. *This operation can't be undone!*\n\n"
            "Note that your account can't be deleted under certain circumstances:\n"
            "- You have any open communisms or refunds or participate in them.\n"
            "- You are vouching for at least one other user.\n"
            "- Your balance is negative.\n"
        )

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        Inform the user about a potentially dangerous operation and send a confirmation inline keyboard
        """

        if update.effective_chat.type != update.effective_chat.PRIVATE:
            await update.effective_message.reply_text("This command can only be used in private chat.")
            return

        try:
            user = await context.application.client.get_core_user(update.effective_message.from_user)
        except err.UniqueUserNotFound:
            await update.effective_message.reply_text("It looks like you don't have any user account yet.")
            return

        self.logger.info(f"User {update.effective_user.id} ({update.effective_user.name}) wants to delete: {user}")
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton(
                "YES",
                callback_data=f"delete_my_account yes {update.effective_user.id} {user.id}"
            ),
            telegram.InlineKeyboardButton(
                "NO",
                callback_data=f"delete_my_account no {update.effective_user.id} {user.id}"
            )
        ]])
        await update.effective_message.reply_text(
            f"_Attention!_ You are asking to delete your user account, including any "
            f"connected aliases, usernames and your balance.\n*This operation can NOT "
            f"be undone!*\n\nAre you *absolutely* sure you want to proceed?",
            parse_mode=telegram.constants.ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
