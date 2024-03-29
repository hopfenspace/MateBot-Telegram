"""
MateBot command executor classes for /data
"""

import time

import telegram

from .. import err, util
from ..base import BaseCommand
from ..parsing.util import Namespace


class DataCommand(BaseCommand):
    """
    Command executor for /data
    """

    def __init__(self):
        super().__init__(
            "data",
            "Show the data the bot has stored about you\n\n"
            "This command can only be used in private chat to protect private data.\n"
            "To view your transactions, use the command `/history` instead."
        )

    async def run(self, args: Namespace, update: telegram.Update) -> None:
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

        try:
            user = await self.client.get_core_user(update.effective_message.from_user)
        except err.MateBotException as exc:
            update.message.reply_text(str(exc))
            return

        if user.external:
            relations = "Voucher user: None"
            if user.voucher_id is not None:
                voucher = await self.client.get_user(user.voucher_id)
                relations = f"Voucher user: {voucher.name}"

        else:
            debtors = list(map(lambda u: u.name, await self.client.get_users(voucher_id=user.id, active=True)))
            relations = f"Debtor user{'s' if len(debtors) != 1 else ''}: {', '.join(debtors) or 'None'}"

        app = await self.client.application
        apps = await self.client.get_applications()
        confirmed_aliases = [
            f'{a.username}@{[c for c in apps if c.id == a.application_id][0].name}'
            for a in user.aliases if a.application_id != app.id and a.confirmed
        ]
        unconfirmed_aliases = [
            f'{a.username}@{[c for c in apps if c.id == a.application_id][0].name}'
            for a in user.aliases if a.application_id != app.id and not a.confirmed
        ]
        votes = await self.client.get_votes(user_id=user.id)
        created_communisms = await self.client.get_communisms(creator_id=user.id)
        created_refunds = await self.client.get_refunds(creator_id=user.id)
        relevant_polls = await self.client.get_polls(user_id=user.id)
        open_created_communisms = [c for c in created_communisms if c.active]
        open_created_refunds = [r for r in created_refunds if r.active]
        open_relevant_polls = [p for p in relevant_polls if p.active]
        transactions = list(sorted(await self.client.get_transactions(member_id=user.id), key=lambda t: t.timestamp))
        last_transaction = (transactions and time.asctime(time.localtime(int(transactions[0].timestamp)))) or None

        result = (
            f"Overview over currently stored data for {user.name}:\n"
            f"\n```\n"
            f"User ID: {user.id}\n"
            f"Telegram ID: {update.effective_message.from_user.id}\n"
            f"Global username: {user.name}\n"
            f"App name: {update.effective_message.from_user.username}\n"
            f"App alias: {update.effective_message.from_user.id}\n"
            f"Confirmed aliases: {', '.join(confirmed_aliases) or 'None'}\n"
            f"Unconfirmed (disabled) aliases: {', '.join(unconfirmed_aliases) or 'None'}\n\n"
            f"Balance: {self.client.format_balance(user)}\n"
            f"Extended permissions: {user.permission}\n"
            f"External user: {user.external}\n"
            f"{relations}\n"
            f"Created communisms: {len(created_communisms)} ({len(open_created_communisms)} open)\n"
            f"Created refunds: {len(created_refunds)} ({len(open_created_refunds)} open)\n"
            f"Relevant polls: {len(relevant_polls)} ({len(open_relevant_polls)} open)\n"
            f"Total votes in refunds and polls: {len(votes)}\n"
            f"Account created: {time.asctime(time.localtime(int(user.created)))}\n"
            f"Last transaction: {last_transaction}\n"
            f"```\n\n"
            f"Use the /history command to see your transaction log."
        )

        util.safe_call(
            lambda: update.effective_message.reply_markdown(result),
            lambda: update.effective_message.reply_text(result)
        )
