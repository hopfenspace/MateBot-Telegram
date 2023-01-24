"""
MateBot command executor class for /donate
"""

import telegram

from .command import BaseCommand
from .. import _common
from ...parsing.types import amount_type
from ...parsing.util import Namespace


class DonateCommand(BaseCommand):
    """
    Command executor for /donate
    """

    def __init__(self):
        super().__init__(
            "donate",
            "Donate money to the community\n\n"
            "Performing this command allows you to transfer money to the "
            "community user. It works similar to the /send operation."
        )

        self.parser.add_argument("amount", type=amount_type)

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

        msg = update.effective_message
        issuer = await context.application.client.get_core_user(msg.from_user)
        if issuer.privilege < issuer.privilege.VOUCHED:
            await msg.reply_text("You are not permitted to use this feature. See /help for details.")
            return

        formatted_amount = context.application.client.format_balance(args.amount)
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton("CONFIRM", callback_data=f"donate confirm {args.amount} {msg.from_user.id}"),
            telegram.InlineKeyboardButton("ABORT", callback_data=f"donate abort {args.amount} {msg.from_user.id}")
        ]])
        await msg.reply_text(f"Do you want to donate {formatted_amount} to the community?", reply_markup=keyboard)
