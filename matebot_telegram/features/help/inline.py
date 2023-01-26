"""
Inline query handler for help queries
"""

import datetime
from typing import Optional

import telegram

from . import common
from ..base import BaseCommand, BaseInlineQuery


class HelpInlineQuery(BaseInlineQuery):
    """
    Get inline help messages like /help does as command
    """

    def get_result_id(self, *args) -> str:
        """
        Generate a result ID based on the current time and the static word ``help``

        :param args: ignored collection of parameters
        :return: result ID for any inline query seeking for help
        """

        if len(args) == 0:
            return f"help-{str(datetime.datetime.now().timestamp()).replace('.', '-')}"
        return f"help-{str(datetime.datetime.now().timestamp()).replace('.', '-')}-{args[0]}"

    def get_command_help(self, command: str) -> Optional[telegram.InlineQueryResult]:
        """
        Get the help message for a specific command requested as possible answer

        :param command: name of one of the supported commands
        :return: optional help message as inline query result for one specific command
        """

        if command not in BaseCommand.AVAILABLE_COMMANDS:
            return

        text = common.get_help_for_command(BaseCommand.AVAILABLE_COMMANDS[command])
        return self.get_result(f"Help on /{command}", text, command, parse_mode=telegram.constants.ParseMode.MARKDOWN)

    def get_help(self) -> telegram.InlineQueryResult:
        """
        Get the generic help message as only answer of an inline query handled by this class

        :return: help message as inline query result
        """

        return self.get_result(
            "Help",
            "This bot provides inline support. To get more information about inline "
            "bots, look at [the Telegram blog](https://telegram.org/blog/inline-bots).\n\n"
            "Currently, the inline support is limited to showing help pages for various commands. "
            "This feature set may be extended in future versions of the bot.",
            parse_mode=telegram.constants.ParseMode.MARKDOWN
        )

    async def run(self, query: telegram.InlineQuery) -> None:
        """
        Answer the inline query by providing the result of :meth:`get_help`

        :param query: inline query as part of an incoming Update
        :return: None
        """

        first_word = query.query.split(" ")[0]
        if first_word.lower() in BaseCommand.AVAILABLE_COMMANDS:
            await query.answer([self.get_command_help(first_word.lower())])
        else:
            await query.answer([self.get_help()] + [
                self.get_command_help(c.lower())
                for c in BaseCommand.AVAILABLE_COMMANDS
                if c.lower().startswith(first_word)
            ])
