"""
MateBot command executor classes for /balance
"""

import telegram

from matebot_telegram import util
from matebot_telegram.connector import APIConnector
from matebot_telegram.base import BaseCommand
from matebot_telegram.parsing.types import user as user_type
from matebot_telegram.parsing.util import Namespace


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

    def run(self, args: Namespace, update: telegram.Update, connect: APIConnector) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        if args.user:
            update.effective_message.reply_text(f"Balance of {args.user.name} is: {args.user.balance / 100 : .2f}€")
        else:
            balance = util.get_user_by_telegram_id(update.effective_message.from_user.id, connect).balance
            update.effective_message.reply_text(f"Your balance is: {balance / 100 :.2f}€")
