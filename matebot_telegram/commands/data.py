"""
MateBot command executor classes for /data
"""

import time

import telegram

from .. import connector, util
from ..base import BaseCommand
from ..parsing.util import Namespace


class DataCommand(BaseCommand):
    """
    Command executor for /data
    """

    def __init__(self):
        super().__init__(
            "data",
            "Use this command to see the data the bot has stored about you.\n\n"
            "This command can only be used in private chat to protect private data.\n"
            "To view your transactions, use the command `/history` instead."
        )

    def run(self, args: Namespace, update: telegram.Update, connect: connector.APIConnector) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        if update.effective_message.chat.type != telegram.Chat.PRIVATE:
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = util.get_user_by(update.effective_message.from_user, update.effective_message.reply_text, connect)
        if user is None:
            return

        if user.external:
            relations = "Voucher user: None"
            if user.voucher is not None:
                voucher = util.get_user_by(user.voucher, lambda: None, connect)
                if voucher is not None:
                    relations = f"Voucher user: {voucher.username}"

        else:
            # TODO: implement this metric
            # users = ", ".join(map(
            #     lambda u: f"{u.name} ({u.username})" if u.username else u.name,
            #     map(
            #         lambda i: MateBotUser(i),
            #         user.debtors
            #     )
            # ))
            # if len(users) == 0:
            #     users = "None"
            # relations = f"Debtor user{'s' if len(users) != 1 else ''}: {users}"
            relations = "Debtor users: ???"

        aliases = ", ".join([f"{a.app_user_id}@{a.application}" for a in user.aliases])

        result = (
            f"Overview over currently stored data for {user.name}:\n"
            f"\n```\n"
            f"User ID: {user.id}\n"
            f"Telegram ID: {update.effective_message.from_user.id}\n"
            f"Name: {user.name}\n"
            f"Username: {user.username}\n"
            f"Balance: {user.balance / 100 :.2f}€\n"
            f"Permissions: {user.permission}\n"
            f"External user: {user.external}\n"
            f"{relations}\n"
            f"Account created: {time.asctime(time.localtime(user.created))}\n"
            f"Last transaction: {time.asctime(time.localtime(user.accessed))}\n"
            f"Aliases: {aliases}"
            f"```\n\n"
            f"Use the /history command to see your transaction log."
        )

        util.safe_call(
            lambda: update.effective_message.reply_markdown(result),
            lambda: update.effective_message.reply_text(result)
        )
