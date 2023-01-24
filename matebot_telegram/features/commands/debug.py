"""
MateBot command executor classes for /debug
"""

import threading

import telegram

from .base import BaseCommand
from ...parsing.util import Namespace


class DebugCommand(BaseCommand):
    """
    Command executor for /debug
    """

    def __init__(self):
        super().__init__(
            "debug",
            "Debugging"
        )

        self.parser.add_argument("cmd", nargs="?")

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        print("T2", threading.current_thread(), threading.enumerate())

        async def me():
            await update.effective_message.reply_text(str(await self.client.get_core_user(update.effective_message.from_user)))

        async def get_community():
            await update.effective_message.reply_text(str(await self.client.get_community_user()))

        async def all_users():
            await update.effective_message.reply_text(str(await self.client.get_users()))

        async def app():
            await update.effective_message.reply_text(str(await self.client.get_applications()))

        async def transactions():
            await update.effective_message.reply_text(str(await self.client.get_transactions()))

        commands = {func.__name__: func for func in [me, get_community, all_users, app, transactions]}

        if args.cmd is None:
            await update.effective_message.reply_text(", ".join(commands.keys()))

        elif args.cmd in commands:
            await commands[args.cmd]()

        else:
            await update.effective_message.reply_text("Unknown command")
