"""
MateBot command executor classes for /zwegat
"""

import telegram
from matebot_sdk.schemas import PrivilegeLevel

from ..base import BaseCommand
from ..parsing.util import Namespace


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

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = update.effective_message.from_user
        user = await self.client.get_core_user(sender)
        if user.privilege < PrivilegeLevel.INTERNAL:
            update.effective_message.reply_text("You are not permitted to use this command. See /help for details.")
            return

        balance = (await self.client.community).balance
        if balance >= 0:
            msg = f"Peter errechnet ein massives Vermögen von {self.client.format_balance(balance)}!"
        else:
            msg = f"Peter errechnet Gesamtschulden von {self.client.format_balance(-balance)}!"
        update.effective_message.reply_text(msg)
