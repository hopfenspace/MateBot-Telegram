"""
MateBot command executor classes for /blame
"""

import telegram
from matebot_sdk.exceptions import MateBotSDKException

from ..base import BaseCommand
from ..parsing.types import natural as natural_type
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
        self.parser.add_argument("count", default=1, type=natural_type, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = await self.client.get_core_user(update.effective_message.from_user)
        try:
            debtors = await self.client.find_sponsors(user, args.count)
            if len(debtors) == 0:
                msg = "Good news! No one has to be blamed, all users have positive balances!"
            elif len(debtors) == 1:
                msg = f"The user with the highest debt is:\n{debtors[0].name}"
            else:
                msg = f"The users with the highest debts are:\n{', '.join(map(lambda u: u.name, debtors))}"
        except MateBotSDKException as exc:
            msg = exc.message
        update.effective_message.reply_text(msg)
