"""
MateBot command executor class for /help
"""

import telegram

from . import common
from ...base import BaseCommand, err, ExtendedContext, Namespace, types


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

        self.parser.add_argument("command", type=types.command, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        Provide the general help page or a specific command manual to a user
        """

        if args.command:
            msg = common.get_help_for_command(args.command)
        else:
            try:
                user = await context.application.client.get_core_user(update.effective_message.from_user)
            except (err.UniqueUserNotFound, err.UserNotVerified, err.NoUserFound):
                msg = await common.get_help_usage(self.usage, None)
                await update.effective_message.reply_markdown(msg)
                return
            except err.MateBotException:
                msg = await common.get_help_usage(self.usage, None)
                await update.effective_message.reply_markdown(msg)
                raise
            msg = await common.get_help_usage(self.usage, user)

        await update.effective_message.reply_markdown(msg)
