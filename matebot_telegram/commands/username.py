"""
MateBot command executor classes for /username
"""

import telegram

from matebot_sdk.exceptions import MateBotSDKException

from .. import err
from ..base import BaseCommand
from ..parsing.util import Namespace


class UsernameCommand(BaseCommand):
    """
    Command executor for /username
    """

    def __init__(self):
        super().__init__(
            "username",
            "Use this command to show or update your global MateBot username.\n\n"
            "This username will be used across all applications running with the "
            "same MateBot core application. Usernames must therefore be unique."
        )
        self.parser.add_argument("username", type=str, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        try:
            user = await self.client.get_core_user(update.effective_message.from_user)
        except err.MateBotException:
            update.effective_message.reply_text("You need to register before using the bot. Use /start to do so.")
            return

        if args.username is None:
            update.effective_message.reply_text(f"Your global username is: '{user.name}'")

        else:
            try:
                user = await self.client.set_username(args.username, user.id)
            except MateBotSDKException as exc:
                update.effective_message.reply_text(exc.message)
            else:
                update.effective_message.reply_text(f"Your global username has been updated to {user.name!r}!")
