"""
MateBot command executor class for /history
"""

import csv
import json
import time
import tempfile

import telegram
from matebot_sdk import schemas

from ..base import BaseCommand, ExtendedContext, Namespace, types


class HistoryCommand(BaseCommand):
    """
    Command executor for /history
    """

    def __init__(self):
        super().__init__(
            "history",
            "Get an overview of your past transactions\n\n"
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
            type=types.natural
        )
        self.parser.new_usage().add_argument(
            "export",
            nargs="?",
            type=lambda x: str(x).lower(),
            choices=("json", "csv")
        )

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

        if args.export is None:
            await self.handle_report(args, update, context)
        else:
            await self.handle_export(args, update, context)

    @staticmethod
    async def handle_export(args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        Handle the request to export the full transaction log of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: ExtendedContext
        :return: None
        """

        if update.effective_chat.type != update.effective_chat.PRIVATE:
            await update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = await context.application.client.get_core_user(update.effective_message.from_user)
        transactions = await context.application.client.get_transactions(member_id=user.id)

        def conv_transaction(t: schemas.Transaction) -> dict:
            return {
                "id": t.id,
                "amount": t.amount,
                "amount_formatted": context.application.client.format_balance(t.amount),
                "sender": t.sender.id,
                "receiver": t.receiver.id,
                "reason": t.reason,
                "registered": t.timestamp,
                "registered_formatted": time.asctime(time.localtime(int(t.timestamp))),
                "multi_transaction": t.multi_transaction_id is not None
            }

        if args.export == "json":
            logs = [conv_transaction(t) for t in transactions]
            if len(logs) == 0:
                await update.effective_message.reply_text("You don't have any registered transactions yet.")
                return

            with tempfile.TemporaryFile(mode="w+b") as file:
                file.write(json.dumps(logs, indent=4).encode("UTF-8"))
                file.seek(0)

                await update.effective_message.reply_document(
                    document=file,
                    filename="transactions.json",
                    caption=(
                        "You requested the export of your transaction log. This file contains "
                        f"all known transactions of {update.effective_message.from_user.name}."
                    )
                )

        elif args.export == "csv":
            logs = [conv_transaction(t) for t in transactions]
            if len(logs) == 0:
                await update.effective_message.reply_text("You don't have any registered transactions yet.")
                return
            fields = list(logs[0].keys())

            with tempfile.TemporaryFile(mode="w+b") as telegram_file:
                with tempfile.TemporaryFile(mode="w+", newline="") as csv_file:
                    writer = csv.DictWriter(csv_file, fieldnames=fields, dialect="unix")
                    writer.writeheader()
                    for row in logs:
                        writer.writerow(row)
                    csv_file.flush()
                    csv_file.seek(0)
                    content = csv_file.read()

                telegram_file.write(content.encode("UTF-8"))
                telegram_file.seek(0)
                await update.effective_message.reply_document(
                    document=telegram_file,
                    filename="transactions.csv",
                    caption=(
                        "You requested the export of your transaction log. "
                        f"This file contains all known transactions of {user.name}."
                    )
                )

    @staticmethod
    async def handle_report(args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        Handle the request to report the most current transaction entries of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: ExtendedContext
        :return: None
        """

        user = await context.application.client.get_core_user(update.effective_message.from_user)

        def format_transaction(transaction: schemas.Transaction) -> str:
            timestamp = time.strftime('%d.%m.%Y %H:%M', time.localtime(int(transaction.timestamp)))
            direction = ["<<", ">>"][transaction.sender.id == user.id]
            partner = ((transaction.sender, transaction.receiver)[transaction.sender.id == user.id]).name
            amount = transaction.amount
            if transaction.sender.id == user.id:
                amount = -amount
            formatted_amount = context.application.client.format_balance(amount)
            return f"{timestamp}: {formatted_amount:>7}: me {direction} {partner:<16} :: {transaction.reason}"

        logs = [
            format_transaction(t)
            for t in await context.application.client.get_transactions(
                member_id=user.id, limit=args.length, descending=True
            )
        ][::-1]

        if len(logs) == 0:
            await update.effective_message.reply_text("You don't have any registered transactions yet.")
            return

        log = "\n".join(logs)
        heading = f"Transaction history for {user.name}:\n```"
        text = f"{heading}\n{log}```"
        if len(text) < 4096:
            await update.effective_message.reply_markdown_v2(text)
            return

        if update.effective_message.chat.type != update.effective_chat.PRIVATE:
            await update.effective_message.reply_text(
                "Your requested transaction logs are too long. Try a smaller "
                "number of entries or execute this command in private chat again."
            )

        else:
            results = [heading]
            for entry in logs:
                if len("\n".join(results + [entry])) > 4096:
                    results.append("```")
                    await update.effective_message.reply_markdown_v2("\n".join(results))
                    results = ["```"]
                results.append(entry)

            if len(results) > 0:
                text = "\n".join(results + ["```"])
                await update.effective_message.reply_markdown_v2(text)
