"""
MateBot command executor class for /start
"""

import telegram.ext

from .command import BaseCommand
from .. import _common
from ... import err
from ...parsing.util import Namespace


class StartCommand(BaseCommand):
    """
    Command executor for /start
    """

    def __init__(self):
        super().__init__(
            "start",
            "Start interacting with this bot, once per user\n\n"
            "This command creates your user account in case it was not yet. Otherwise, "
            "this command might not be pretty useful. Note that you should not delete "
            "the chat with the bot in order to receive personal notifications from it.\n\n"
            "Use /help for more information about how to use this bot and its commands."
        )

    async def run(self, args: Namespace, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: _common.ExtendedContext
        :return: None
        """

        sender = update.effective_message.from_user
        if sender.is_bot:
            return

        if update.message.chat.type != telegram.Chat.PRIVATE:
            await update.message.reply_text("This command should be executed in private chat.")
            return

        try:
            await context.application.client.get_core_user(sender)
            await update.message.reply_text("You are already registered. Using this command twice has no means.")
            return
        except err.UniqueUserNotFound:
            pass
        except err.MateBotException as exc:
            await update.message.reply_text(str(exc))
            return

        await update.message.reply_text(
            "It looks like you are a new user. Did you already use the MateBot in some other application?",
            reply_markup=telegram.InlineKeyboardMarkup([[
                telegram.InlineKeyboardButton("YES", callback_data=f"start init {sender.id} existing"),
                telegram.InlineKeyboardButton("NO", callback_data=f"start init {sender.id} new")
            ]])
        )
