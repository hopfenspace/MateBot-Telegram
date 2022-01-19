"""
MateBot command executor classes for /history
"""

import json
import time
import tempfile

import telegram
from matebot_sdk import schemas

from .. import util
from ..base import BaseCommand
from ..client import SDK
from ..parsing.types import natural as natural_type
from ..parsing.util import Namespace


class HistoryCommand(BaseCommand):
    """
    Command executor for /history
    """

    def __init__(self):
        super().__init__(
            "history",
            "Use this command to get an overview of your transactions.\n\n"
            "You can specify the number of most recent transactions (default "
            "10) which will be returned by the bot. Using a huge number will "
            "just print all your transactions, maybe in multiple messages.\n\n"
            "You could also export the whole history of your personal transactions "
            "as downloadable file. Currently supported formats are `csv` and `json`. "
            "Just add one of those two format specifiers after the command. Note "
            "that this variant is restricted to your personal chat with the bot."
        )

        self.parser.add_argument(
            "length",
            nargs="?",
            default=10,
            type=natural_type
        )
        self.parser.new_usage().add_argument(
            "export",
            nargs="?",
            type=lambda x: str(x).lower(),
            choices=("json", "csv")
        )

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.export is None:
            await self._handle_report(args, update)
        else:
            await self._handle_export(args, update)

    @staticmethod
    async def _handle_export(args: Namespace, update: telegram.Update) -> None:
        """
        Handle the request to export the full transaction log of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if update.effective_chat.type != update.effective_chat.PRIVATE:
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = await SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
        transactions = await SDK.get_transactions_of_user(user)

        if args.export == "json":
            logs = [t.json() for t in transactions]
            if len(logs) == 0:
                update.effective_message.reply_text("You don't have any registered transactions yet.")
                return

            with tempfile.TemporaryFile(mode="w+b") as file:
                file.write(json.dumps(logs, indent=4).encode("UTF-8"))
                file.seek(0)

                update.effective_message.reply_document(
                    document=file,
                    filename="transactions.json",
                    caption=(
                        "You requested the export of your transaction log. This file contains "
                        f"all known transactions of {update.effective_message.from_user.name}."
                    )
                )

        elif args.export == "csv":
            # TODO: implement CSV export of transactions
            update.effective_message.reply_text("This feature is not implemented yet.")
            return

            # content = TransactionLog(user).to_csv(True)
            # if content is None:
            #     update.effective_message.reply_text("You don't have any registered transactions yet.")
            #     return
            #
            # with tempfile.TemporaryFile(mode="w+b") as file:
            #     file.write(content.encode("UTF-8"))
            #     file.seek(0)
            #
            #     update.effective_message.reply_document(
            #         document=file,
            #         filename="transactions.csv",
            #         caption=(
            #             "You requested the export of your transaction log. "
            #             f"This file contains all known transactions of {user.name}."
            #         )
            #     )

    @staticmethod
    async def _handle_report(args: Namespace, update: telegram.Update) -> None:
        """
        Handle the request to report the most current transaction entries of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = await SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))

        def format_transaction(transaction: schemas.Transaction):
            timestamp = time.strftime('%d.%m.%Y %H:%M', time.localtime(transaction.timestamp))
            direction = ["<<", ">>"][transaction.sender.id == user.id]
            partner = SDK.get_username([transaction.sender, transaction.receiver][transaction.sender.id == user.id])
            amount = transaction.amount / 100
            if transaction.sender.id == user.id:
                amount = -amount
            return f"{timestamp}: {amount:>+7.2f}: me {direction} {partner:<16} :: {transaction.reason}"

        logs = [format_transaction(t) for t in await SDK.get_transactions_of_user(user)][-args.length:]
        name = SDK.get_username(user)

        if len(logs) == 0:
            update.effective_message.reply_text("You don't have any registered transactions yet.")
            return

        log = "\n".join(logs)
        heading = f"Transaction history for {name}:\n```"
        text = f"{heading}\n{log}```"
        if len(text) < 4096:
            util.safe_call(
                lambda: update.effective_message.reply_markdown_v2(text),
                lambda: update.effective_message.reply_text(text)
            )
            return

        if update.effective_message.chat.type != update.effective_chat.PRIVATE:
            update.effective_message.reply_text(
                "Your requested transaction logs are too long. Try a smaller "
                "number of entries or execute this command in private chat again."
            )

        else:
            results = [heading]
            for entry in logs:
                if len("\n".join(results + [entry])) > 4096:
                    results.append("```")
                    util.safe_call(
                        lambda: update.effective_message.reply_markdown_v2("\n".join(results)),
                        lambda: update.effective_message.reply_text("\n".join(results))
                    )
                    results = ["```"]
                results.append(entry)

            if len(results) > 0:
                text = "\n".join(results + ["```"])
                util.safe_call(
                    lambda: update.effective_message.reply_markdown_v2(text),
                    lambda: update.effective_message.reply_text(text)
                )
