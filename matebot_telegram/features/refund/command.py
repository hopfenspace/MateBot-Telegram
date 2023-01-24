"""
MateBot command executor class for /refund
"""

from typing import ClassVar

import telegram

from .command import BaseCommand
from .. import _common
from ... import shared_messages, util
from ..common.refund import get_text, get_keyboard
from ...parsing.actions import JoinAction
from ...parsing.types import amount_type
from ...parsing.util import Namespace


class RefundCommand(BaseCommand):
    """
    Command executor for /refund
    """

    # Set the actual command name (for the UI), since this class is subclassed as alias for /pay
    COMMAND_NAME: ClassVar[str] = "refund"

    def __init__(self):
        super().__init__(
            type(self).COMMAND_NAME,
            f"Create a {type(self).COMMAND_NAME} request\n\n"
            f"When you want to get money from the community, a {type(self).COMMAND_NAME} "
            "request needs to be created. It requires an amount and a description. "
            "The community members with vote permissions will then vote for or against "
            "your request to verify that your request is valid and legitimate. "
            "In case it's approved, the community will send the money to you.\n\n"
            "There are two subcommands that can be used. You can get your "
            "active request as a new message in the current chat by using `show`. "
            "You can stop your currently active refund request using `stop`."
        )

        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", action=JoinAction, nargs="*")

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = await self.client.get_core_user(update.effective_message.from_user)

        if args.subcommand is None:
            return await _common.new_group_operation(
                self.client.create_refund(sender, args.amount, args.reason),
                self.client,
                lambda p: get_text(None, p),
                get_keyboard,
                update.effective_message,
                shared_messages.ShareType.REFUND,
                self.logger
            )

        active_refunds = await self.client.get_refunds(active=True, creator_id=sender.id)
        if not active_refunds:
            await update.effective_message.reply_text(f"You don't have a {type(self).COMMAND_NAME} request in progress.")
            return

        if len(active_refunds) > 1:
            await update.effective_message.reply_text(
                f"You have more than one active {type(self).COMMAND_NAME} request. "
                f"The command will affect the most recent active {type(self).COMMAND_NAME} request."
            )

        if args.subcommand == "show":
            _common.show_updated_group_operation(
                self.client,
                update.effective_message,
                await get_text(None, active_refunds[-1]),
                get_keyboard(active_refunds[-1]),
                shared_messages.ShareType.REFUND,
                active_refunds[-1].id,
                self.logger
            )

        elif args.subcommand == "stop":
            aborted_refund = await self.client.abort_refund(active_refunds[-1], sender)
            text = await get_text(None, aborted_refund)
            keyboard = get_keyboard(aborted_refund)

            util.update_all_shared_messages(
                update.effective_message.bot,
                shared_messages.ShareType.REFUND,
                aborted_refund.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                delete_shared_messages=True
            )
