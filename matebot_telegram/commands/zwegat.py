"""
MateBot command executor classes for /zwegat
"""

import logging

import telegram
from matebot_sdk.base import PermissionLevel

from ..base import BaseCommand
from ..client import SDK
from ..parsing.util import Namespace


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

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = await SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
        permission_check = SDK.ensure_permissions(sender, PermissionLevel.ANY_INTERNAL, "zwegat")
        if not permission_check[0]:
            update.effective_message.reply_text(permission_check[1])
            return

        community = await SDK.get_community_user()

        total = community.balance / 100
        if total >= 0:
            update.effective_message.reply_text(f"Peter errechnet ein massives Vermögen von {total:.2f}€")
        else:
            update.effective_message.reply_text(f"Peter errechnet Gesamtschulden von {-total:.2f}€")
