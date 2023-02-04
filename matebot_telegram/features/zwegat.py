"""
MateBot command executor class for /zwegat
"""

import telegram
from matebot_sdk.schemas import PrivilegeLevel

from ..base import BaseCommand, ExtendedContext, Namespace


class ZwegatCommand(BaseCommand):
    """
    Command executor for /zwegat
    """

    def __init__(self):
        super().__init__(
            "zwegat",
            "Show the central funds\n\n"
            "This command can only be used by internal users."
        )

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

        sender = update.effective_message.from_user
        user = await context.application.client.get_core_user(sender)
        if user.privilege < PrivilegeLevel.INTERNAL:
            await update.effective_message.reply_text(
                "You are not permitted to use this command. See /help for details."
            )
            return

        balance = (await context.application.client.community).balance
        if balance >= 0:
            msg = f"Peter errechnet ein massives Vermögen von {context.application.client.format_balance(balance)}!"
        else:
            msg = f"Peter errechnet Gesamtschulden von {context.application.client.format_balance(-balance)}!"
        await update.effective_message.reply_text(msg)
