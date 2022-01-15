"""
MateBot command executor classes for /data
"""

import time

import telegram

from .. import util
from ..base import BaseCommand
from ..client import SDK
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

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if update.effective_message.chat.type != telegram.Chat.PRIVATE:
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = util.get_event_loop().run_until_complete(
            SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
        )

        if user.external:
            relations = "Voucher user: None"
            if user.voucher_id is not None:
                voucher = util.get_event_loop().run_until_complete(SDK.get_user_by_id(user.voucher_id))
                relations = f"Voucher user: {SDK.get_username(voucher)}"

        else:
            all_users = util.get_event_loop().run_until_complete(SDK.get_users())
            debtors = [SDK.get_username(u) for u in all_users if u.voucher_id == user.id]
            relations = f"Debtor user{'s' if len(debtors) != 1 else ''}: {', '.join(debtors) or 'None'}"

        app = util.get_event_loop().run_until_complete(SDK.application)
        apps = util.get_event_loop().run_until_complete(SDK.get_applications())
        other_aliases = [
            f'{a.app_username}@{[c for c in apps if c.id == a.application_id][0].name}'
            for a in user.aliases if a.application_id != app.id
        ]
        votes = util.get_event_loop().run_until_complete(SDK.get_votes())
        my_votes = [v for v in votes if v.user_id == user.id]
        created_communisms = util.get_event_loop().run_until_complete(SDK.get_communisms_by_creator(user))
        created_refunds = util.get_event_loop().run_until_complete(SDK.get_refunds_by_creator(user))
        open_created_communisms = [c for c in created_communisms if c.active]
        open_created_refunds = [r for r in created_refunds if r.active]

        result = (
            f"Overview over currently stored data for {user.name}:\n"
            f"\n```\n"
            f"User ID: {user.id}\n"
            f"Telegram ID: {update.effective_message.from_user.id}\n"
            f"Username: {user.name}\n"
            f"App name: {update.effective_message.from_user.username}\n"
            f"Balance: {user.balance / 100 :.2f}€\n"
            f"Permissions: {user.permission}\n"
            f"External user: {user.external}\n"
            f"{relations}\n"
            f"Created communisms: {len(created_communisms)} ({len(open_created_communisms)} open)\n"
            f"Created refunds: {len(created_refunds)} ({len(open_created_refunds)} open)\n"
            f"Votes in polls: {len(my_votes)}\n"
            f"Account created: {time.asctime(time.localtime(user.created))}\n"
            f"Last transaction: {time.asctime(time.localtime(user.accessed))}\n"
            f"App aliases: {', '.join([f'{a.app_username}' for a in user.aliases if a.application_id == app.id])}\n"
            f"Other aliases: {', '.join(other_aliases) or 'None'}"
            f"```\n\n"
            f"Use the /history command to see your transaction log."
        )

        util.safe_call(
            lambda: update.effective_message.reply_markdown(result),
            lambda: update.effective_message.reply_text(result)
        )
