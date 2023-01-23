"""
MateBot command executor class for /help
"""

from typing import Optional

import telegram
from matebot_sdk import exceptions, schemas

from .base import BaseCommand
from .. import _common
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
            msg = self.get_help_for_command(args.command)
        else:
            try:
                user = await context.application.client.get_core_user(update.effective_message.from_user)
            except (err.MateBotException, exceptions.APIConnectionException):
                msg = await self.get_help_usage(self.usage, context, None)
                await util.safe_call(
                    lambda: update.effective_message.reply_markdown(msg),
                    lambda: update.effective_message.reply_text(msg)
                )
                raise
            msg = await self.get_help_usage(self.usage, context, user)

        await util.safe_call(
            lambda: update.effective_message.reply_markdown(msg),
            lambda: update.effective_message.reply_text(msg)
        )

    async def get_help_usage(self, usage: str, context: _common.ExtendedContext, user: Optional[schemas.User] = None) -> str:
        """
        Retrieve the help message from the help command without arguments

        :param usage: usage string of the help command
        :type usage: str
        :param context: the custom context of the application
        :type context: _common.ExtendedContext
        :param user: optional User who issued the help command
        :type user: Optional[matebot_sdk.schemas.User]
        :return: fully formatted help message when invoking the help command without arguments
        :rtype: str
        """

        command_list = "\n".join(map(lambda c: f" - `{c}`", sorted(BaseCommand.AVAILABLE_COMMANDS.keys())))
        msg = f"*MateBot Telegram help page*\n\nUsage of this command: `{usage}`\n\nList of commands:\n{command_list}"
        dynamic_commands = "\n".join(sorted(
            [f"- `{c.name}` for {context.application.client.format_balance(c.price)}" for c in await context.application.client.get_consumables()]
        ))
        msg += f"\n\nAdditionally, the following dynamic consumption commands are available:\n{dynamic_commands}"

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
                    "<your username>`. Afterwards, you may use this bot.\n"
                    "Alternatively, use the /poll command to request access "
                    "to the internal group by community approval."
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
