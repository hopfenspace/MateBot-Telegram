"""
MateBot command executor classes for /balance
"""

import telegram

from ..base import BaseCommand
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

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.user:
            update.effective_message.reply_text(
                f"Balance of {args.user.name} is: {self.client.format_balance(args.user)}"
            )
        else:
            user = await self.client.get_core_user(update.effective_message.from_user)
            update.effective_message.reply_text(f"Your balance is: {self.client.format_balance(user)}")
