"""
MateBot command executor class for /help
"""

import telegram
from matebot_sdk import exceptions

from .command import BaseCommand
from .. import _common
from ..common import help as _help
from ... import err, util
from ...parsing.types import command as command_type
from ...parsing.util import Namespace


class HelpCommand(BaseCommand):
    """
    Command executor for /help
    """

    def __init__(self):
        super().__init__(
            "help",
            "List available commands with helpful information and inspect their usage\n\n"
            "The `/help` command prints the help page for any "
            "command. If no argument is passed, it will print its "
            "usage and a list of all available commands.",
            "/help [command]"
        )

        self.parser.add_argument("command", type=command_type, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: _common.ExtendedContext
        :return: None
        """

        if args.command:
            msg = _help.get_help_for_command(args.command)
        else:
            try:
                user = await context.application.client.get_core_user(update.effective_message.from_user)
            except (err.MateBotException, exceptions.APIConnectionException):
                msg = await _help.get_help_usage(self.usage, context.application.client, None)
                await util.safe_call(
                    lambda: update.effective_message.reply_markdown(msg),
                    lambda: update.effective_message.reply_text(msg)
                )
                raise
            msg = await _help.get_help_usage(self.usage, context.application.client, user)

        await util.safe_call(
            lambda: update.effective_message.reply_markdown(msg),
            lambda: update.effective_message.reply_text(msg)
        )
