"""
MateBot command executor classes for /zwegat
"""

import logging

import telegram

from mate_bot import util
from mate_bot.state.user import CommunityUser, MateBotUser
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class ZwegatCommand(BaseCommand):
    """
    Command executor for /zwegat
    """

    def __init__(self):
        super().__init__(
            "zwegat",
            "Use this command to show the central funds.\n\n"
            "This command can only be used by internal users."
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = MateBotUser(update.effective_message.from_user)
        if not self.ensure_permissions(user, 2, update.effective_message):
            return

        if CommunityUser().balance >= 0:
            update.effective_message.reply_text(
                f"Peter errechnet ein massives Vermögen von {util.format_currency(CommunityUser().balance)}"
            )
        else:
            update.effective_message.reply_text(
                f"Peter errechnet Gesamtschulden von -{util.format_currency(CommunityUser().balance)}"
            )
