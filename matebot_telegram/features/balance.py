"""
MateBot command executor class for /balance
"""

import telegram
from matebot_sdk.schemas import PrivilegeLevel

from ..base import BaseCommand, ExtendedContext, Namespace, types


class BalanceCommand(BaseCommand):
    """
    Command executor for /balance
    """

    def __init__(self):
        super().__init__(
            "balance",
            "Show a user's balance\n\n"
            "When you use this command without arguments, the bot will "
            "reply with your current amount of money stored in your virtual "
            "wallet. If you specify a username or mention someone as an argument, "
            "the 'balance' of this user is returned instead of yours."
        )

        self.parser.add_argument("user", type=types.any_user_type, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: ExtendedContext
        :return: None
        """

        user = await context.application.client.get_core_user(update.effective_message.from_user)
        if args.user:
            if user.privilege < PrivilegeLevel.VOUCHED:
                await update.effective_message.reply_text("You are not permitted to use this command.")
            else:
                await update.effective_message.reply_text(
                    f"Balance of {args.user.name} is: {context.application.client.format_balance(args.user)}"
                )
        else:
            await update.effective_message.reply_text(
                f"Your balance is: {context.application.client.format_balance(user)}"
            )
