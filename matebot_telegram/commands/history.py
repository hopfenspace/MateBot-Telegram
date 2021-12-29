"""
MateBot command executor classes for /history
"""

import json
import tempfile

import telegram

from ..base import BaseCommand
from ..parsing.types import natural as natural_type
from ..parsing.util import Namespace
from .. import connector, schemas, util


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

        if args.export is None:
            self._handle_report(args, update, connect)
        else:
            self._handle_export(args, update, connect)

    @staticmethod
    def _handle_export(args: Namespace, update: telegram.Update, connect: connector.APIConnector) -> None:
        """
        Handle the request to export the full transaction log of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        if update.effective_chat.type != update.effective_chat.PRIVATE:
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = util.get_user_by(update.effective_message.from_user, update.effective_message.reply_text, connect)
        if user is None:
            return

        response = connect.get(f"/v1/transactions/user/{user.id}")
        if not response.ok:
            update.effective_message.reply_text("Error processing your request. Please file a bug report.")
            return

        transactions = [schemas.Transaction(**e) for e in response.json()]

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
    def _handle_report(args: Namespace, update: telegram.Update, connect: connector.APIConnector) -> None:
        """
        Handle the request to report the most current transaction entries of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        user = util.get_user_by(update.effective_message.from_user, update.effective_message.reply_text, connect)
        if user is None:
            return

        response = connect.get(f"/v1/transactions/user/{user.id}")
        if not response.ok:
            update.effective_message.reply_text("Error processing your request. Please file a bug report.")
            return

        # TODO: improve the generation of log entries with a custom format
        logs = [str(schemas.Transaction(**e)) for e in response.json()]
        name = update.effective_message.from_user.name

        # TODO: limit the output to the number of requested entries

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
