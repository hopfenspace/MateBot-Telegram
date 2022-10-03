"""
MateBot command executor classes for /help
"""

import datetime
from typing import Optional

import telegram
from matebot_sdk import exceptions, schemas

from .. import err, util
from ..base import BaseCommand, BaseInlineQuery
from ..parsing.types import command as command_type
from ..parsing.util import Namespace


class HelpCommand(BaseCommand):
    """
    Command executor for /help
    """

    def __init__(self):
        super().__init__(
            "help",
            "The `/help` command prints the help page for any "
            "command. If no argument is passed, it will print its "
            "usage and a list of all available commands.",
            "/help [command]"
        )

        self.parser.add_argument("command", type=command_type, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.command:
            msg = self.get_help_for_command(args.command)
        else:
            try:
                user = await self.client.get_core_user(update.effective_message.from_user)
            except (err.MateBotException, exceptions.APIConnectionException):
                msg = self.get_help_usage(self.usage, None)
                util.safe_call(
                    lambda: update.effective_message.reply_markdown(msg),
                    lambda: update.effective_message.reply_text(msg)
                )
                raise
            msg = self.get_help_usage(self.usage, user)

        util.safe_call(
            lambda: update.effective_message.reply_markdown(msg),
            lambda: update.effective_message.reply_text(msg)
        )

    @staticmethod
    def get_help_usage(usage: str, user: Optional[schemas.User] = None) -> str:
        """
        Retrieve the help message from the help command without arguments

        :param usage: usage string of the help command
        :type usage: str
        :param user: optional User who issued the help command
        :type user: Optional[matebot_sdk.schemas.User]
        :return: fully formatted help message when invoking the help command without arguments
        :rtype: str
        """

        command_list = "\n".join(map(lambda c: f" - `{c}`", sorted(BaseCommand.AVAILABLE_COMMANDS.keys())))
        msg = f"*MateBot Telegram help page*\n\nUsage of this command: `{usage}`\n\nList of commands:\n\n{command_list}"

        if user and not user.active:
            msg += "\n\nYour user account has been disabled. You're not allowed to interact with the bot."

        elif user and user.external:
            msg += "\n\nYou are an external user. Some commands may be restricted."

            if user.voucher_id is None:
                msg += (
                    "\nYou don't have any creditor. Your possible interactions "
                    "with the bot are very limited for security purposes. You "
                    "can ask some internal user to act as your voucher. To "
                    "do this, the internal user needs to execute `/vouch "
                    "<your username>`. Afterwards, you may use this bot."
                )

        elif user and user.privilege >= user.privilege.PERMITTED:
            msg += "\n\nYou have been granted extended voting permissions. With great power comes great responsibility."

        return msg

    @staticmethod
    def get_help_for_command(command: BaseCommand) -> str:
        """
        Get the help message for a specific command in Markdown

        :param command: command which should be used for help message generation
        :type command: BaseCommand
        :return: Markdown-enabled help message for a specific command
        :rtype: str
        """

        usages = "\n".join(map(lambda x: f"`/{command.name} {x}`", command.parser.usages))
        return f"*Usages:*\n{usages}\n\n*Description:*\n{command.description}"


class HelpInlineQuery(BaseInlineQuery):
    """
    Get inline help messages like /help does as command
    """

    def get_result_id(self, *args) -> str:
        """
        Generate a result ID based on the current time and the static word ``help``

        :param args: ignored collection of parameters
        :return: result ID for any inline query seeking for help
        :rtype: str
        """

        return f"help-{int(datetime.datetime.now().timestamp())}"

    def get_command_help(self, command: str) -> Optional[telegram.InlineQueryResult]:
        """
        Get the help message for a specific command requested as possible answer

        :param command: name of one of the supported commands, see :mod:`matebot_telegram.registry`
        :type command: str
        :return: help message as inline query result for one specific command
        :rtype: typing.Optional[telegram.InlineQueryResult]
        """

        if command not in BaseCommand.AVAILABLE_COMMANDS:
            return

        text = HelpCommand.get_help_for_command(BaseCommand.AVAILABLE_COMMANDS[command])
        return self.get_result(f"Help on /{command}", text, parse_mode=telegram.ParseMode.MARKDOWN)

    def get_help(self) -> telegram.InlineQueryResult:
        """
        Get the generic help message as only answer of an inline query handled by this class

        :return: help message as inline query result
        :rtype: telegram.InlineQueryResult
        """

        return self.get_result(
            "Help",
            "This bot provides limited inline support. To get more information about inline "
            "bots, look at [the Telegram blog](https://telegram.org/blog/inline-bots).\n\n"
            "Currently, a basic user search to forward communisms (see /communism) and refund "
            "requests (see /refund; an alias for the deprecated command /pay still exists) "
            "is supported. You may have a look at those two commands in order to know "
            "how you might be able to use the inline feature of this bot.\n"
            "You could try out the inline feature with some of the supported commands!",
            parse_mode=telegram.ParseMode.MARKDOWN
        )

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Answer the inline query by providing the result of :meth:`get_help`

        :param query: inline query as part of an incoming Update
        :type query: telegram.InlineQuery
        :return: None
        """

        first_word = query.query.split(" ")[0]
        if first_word.lower() in BaseCommand.AVAILABLE_COMMANDS:
            query.answer([self.get_command_help(first_word.lower())])
        else:
            query.answer([self.get_help()])
