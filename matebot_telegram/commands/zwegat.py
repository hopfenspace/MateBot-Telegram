"""
MateBot command executor classes for /zwegat
"""

import logging

import telegram

from matebot_telegram import schemas, util
from matebot_telegram.base import BaseCommand
from matebot_telegram.connector import APIConnector
from matebot_telegram.parsing.util import Namespace


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

        sender = util.get_user_by_telegram_id(update.effective_message.from_user.id, connect)
        if sender.external or not sender.permission:
            update.effective_message.reply_text("You don't have permission to perform this command.")
            return

        community = schemas.User(**connect.get("/v1/users/community").json())

        total = community.balance / 100
        if total >= 0:
            update.effective_message.reply_text(f"Peter errechnet ein massives Vermögen von {total:.2f}€")
        else:
            update.effective_message.reply_text(f"Peter errechnet Gesamtschulden von {-total:.2f}€")
