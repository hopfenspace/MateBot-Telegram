"""
MateBot command executor classes for /blame
"""

import telegram
from matebot_sdk.base import PermissionLevel

from .. import util
from ..base import BaseCommand
from ..client import SDK
from ..parsing.util import Namespace


class BlameCommand(BaseCommand):
    """
    Command executor for /blame
    """

    def __init__(self):
        super().__init__(
            "blame",
            "Use this command to show the user(s) with the highest debts.\n\n"
            "Put the user(s) with the highest debts to the pillory and make them "
            "settle their debts, e.g. by buying stuff like new bottle crates. "
            "This command can only be executed by internal users."
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = util.get_event_loop().run_until_complete(
            SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
        )
        permission_check = SDK.ensure_permissions(user, PermissionLevel.ANY_INTERNAL, "blame")
        if not permission_check[0]:
            update.effective_message.reply_text(permission_check[1])
            return

        users = util.get_event_loop().run_until_complete(SDK.get_users())
        min_balance = min(users, key=lambda u: u.balance).balance
        debtors = [user for user in users if user.balance <= min_balance and user.balance < 0]
        if len(debtors) == 0:
            msg = "Good news! No one has to be blamed, all users have positive balances!"
        elif len(debtors) == 1:
            msg = f"The user with the highest debt is:\n{SDK.get_username(debtors[0])}"
        else:
            msg = f"The users with the highest debts are:\n{', '.join(map(SDK.get_username, debtors))}"
        update.effective_message.reply_text(msg)
