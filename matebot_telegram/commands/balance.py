"""
MateBot command executor classes for /balance
"""

import telegram

from .. import util
from ..base import BaseCommand
from ..client import SDK
from ..parsing.util import Namespace
from ..parsing.types import user_type


class BalanceCommand(BaseCommand):
    """
    Command executor for /balance
    """

    def __init__(self):
        super().__init__(
            "balance",
            "Use this command to show a user's balance.\n\n"
            "When you use this command without arguments, the bot will "
            "reply with your current amount of money stored in your virtual "
            "wallet. If you specify a username or mention someone as an argument,"
            "the 'balance' of this user is returned instead of yours."
        )

        self.parser.add_argument("user", type=user_type, nargs="?")

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.user:
            update.effective_message.reply_text(
                f"Balance of {SDK.get_username(args.user)} is: {args.user.balance / 100 : .2f}€"
            )
        else:
            user = util.get_event_loop().run_until_complete(
                SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
            )
            update.effective_message.reply_text(f"Your balance is: {user.balance / 100 :.2f}€")
