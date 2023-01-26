"""
MateBot command executor class for /refund
"""

from typing import ClassVar

import telegram

from . import common
from ..base import BaseCommand, ExtendedContext, Namespace, types
from .. import _common  # TODO: Rework to finally drop this import
from ... import shared_messages, util
from ...parsing.actions import JoinAction


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

        self.parser.add_argument("amount", type=types.amount_type)
        self.parser.add_argument("reason", action=JoinAction, nargs="*")

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        TODO
        """

        sender = await context.application.client.get_core_user(update.effective_message.from_user)

        if args.subcommand is None:
            return await _common.new_group_operation(
                context.application.client.create_refund(sender, args.amount, args.reason),
                context.application.client,
                lambda p: common.get_text(None, p),
                common.get_keyboard,
                update.effective_message,
                shared_messages.ShareType.REFUND,
                self.logger
            )

        active_refunds = await context.application.client.get_refunds(active=True, creator_id=sender.id)
        if not active_refunds:
            await update.effective_message.reply_text(f"You don't have a {type(self).COMMAND_NAME} request in progress.")
            return

        if len(active_refunds) > 1:
            await update.effective_message.reply_text(
                f"You have more than one active {type(self).COMMAND_NAME} request. "
                f"The command will affect the most recent active {type(self).COMMAND_NAME} request."
            )

        if args.subcommand == "show":
            await _common.show_updated_group_operation(
                context.application.client,
                update.effective_message,
                await common.get_text(None, active_refunds[-1]),
                common.get_keyboard(active_refunds[-1]),
                shared_messages.ShareType.REFUND,
                active_refunds[-1].id,
                self.logger
            )

        elif args.subcommand == "stop":
            aborted_refund = await context.application.client.abort_refund(active_refunds[-1], sender)
            text = await common.get_text(None, aborted_refund)
            keyboard = common.get_keyboard(aborted_refund)

            util.update_all_shared_messages(
                context.bot,
                shared_messages.ShareType.REFUND,
                aborted_refund.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                delete_shared_messages=True
            )