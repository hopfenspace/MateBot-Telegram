"""
MateBot command executor class for /username
"""

import telegram

from matebot_sdk.exceptions import MateBotSDKException

from .command import BaseCommand
from .. import _common
from ... import err
from ...parsing.util import Namespace


class UsernameCommand(BaseCommand):
    """
    Command executor for /username
    """

    def __init__(self):
        super().__init__(
            "username",
            "Show or update your global MateBot username\n\n"
            "This username will be used across all applications running with the "
            "same MateBot core application. Usernames must therefore be unique."
        )
        self.parser.add_argument("username", type=str, nargs="?")

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

        try:
            user = await context.application.client.get_core_user(update.effective_message.from_user)
        except err.MateBotException:
            await update.effective_message.reply_text("You need to register before using the bot. Use /start to do so.")
            return

        if args.username is None:
            await update.effective_message.reply_text(f"Your global username is: '{user.name}'")

        else:
            try:
                user = await context.application.client.set_username(args.username, user.id)
            except MateBotSDKException as exc:
                await update.effective_message.reply_text(exc.message)
            else:
                await update.effective_message.reply_text(f"Your global username has been updated to {user.name!r}!")
