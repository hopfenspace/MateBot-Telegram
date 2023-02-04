"""
MateBot command executor class for /blame
"""

import telegram
from matebot_sdk.exceptions import MateBotSDKException

from ..base import BaseCommand, ExtendedContext, Namespace, types


class BlameCommand(BaseCommand):
    """
    Command executor for /blame
    """

    def __init__(self):
        super().__init__(
            "blame",
            "Show the user(s) with the highest debts\n\n"
            "Put the user(s) with the highest debts to the pillory and make them "
            "settle their debts, e.g. by buying stuff like new bottle crates. "
            "This command can only be executed by internal users."
        )
        self.parser.add_argument("count", default=1, type=types.natural, nargs="?")

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
        try:
            debtors = await context.application.client.find_sponsors(user, args.count)
            if len(debtors) == 0:
                msg = "Good news! No one has to be blamed, all users have positive balances!"
            elif len(debtors) == 1:
                msg = f"The user with the highest debt is:\n{debtors[0].name}"
            else:
                msg = f"The users with the highest debts are:\n{', '.join(map(lambda u: u.name, debtors))}"
        except MateBotSDKException as exc:
            msg = exc.message
        await update.effective_message.reply_text(msg)
