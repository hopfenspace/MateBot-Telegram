"""
MateBot command executor class for /communism
"""

import telegram.ext

from .base import BaseCommand
from .. import _common
from ..common import communism
from ... import shared_messages, util
from ...parsing.types import amount_type
from ...parsing.actions import JoinAction
from ...parsing.util import Namespace


class CommunismCommand(BaseCommand):
    """
    Command executor for /communism

    Note that the majority of the functionality is located in the query handler.
    """

    def __init__(self):
        super().__init__(
            "communism",
            "Start, stop or show a communism to split bills among several users\n\n"
            "When you pay for something that is used or otherwise consumed by a bigger "
            "group of people, you can open a communism for it to get your money back.\n\n"
            "When you use this command, you specify a reason and the price. The others "
            "can join afterwards (you might need to remember them). People who don't use "
            "the MateBot may be respected by joining multiple times - therefore paying more "
            "than normal and effectively taking the bill of those people. You may collect "
            "the money from each unregistered user by yourself. After everyone has joined, "
            "you close the communism to calculate and evenly distribute the price.\n\n"
            "There are two subcommands that can be used. You can get your most recent "
            "active communism as a new message in the current chat by using `show`. "
            "You can stop your most recent, currently active communism using `stop`."
        )

        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", nargs="+", action=JoinAction)

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    async def run(self, args: Namespace, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param context: the custom context of the application
        :type context: _common.ExtendedContext
        :return: None
        """

        user = await context.application.client.get_core_user(update.effective_message.from_user)

        if args.subcommand is None:
            return await _common.new_group_operation(
                context.application.client.create_communism(user, args.amount, args.reason),
                context.application.client,
                lambda c: get_text(context.application.client, c),
                get_keyboard,
                update.effective_message,
                shared_messages.ShareType.COMMUNISM,
                self.logger
            )

        active_communisms = await context.application.client.get_communisms(active=True, creator_id=user.id)
        if not active_communisms:
            await update.effective_message.reply_text("You don't have a communism in progress.")
            return

        if args.subcommand == "show":
            _common.show_updated_group_operation(
                self.client,
                update.effective_message,
                await get_text(self.client, active_communisms[-1]),
                get_keyboard(active_communisms[-1]),
                shared_messages.ShareType.COMMUNISM,
                active_communisms[-1].id,
                self.logger
            )

        elif args.subcommand == "stop":
            aborted_communism = await self.client.abort_communism(active_communisms[-1], user)
            text = await get_text(self.client, aborted_communism)
            keyboard = get_keyboard(aborted_communism)

            util.update_all_shared_messages(
                update.effective_message.bot,
                shared_messages.ShareType.COMMUNISM,
                aborted_communism.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                delete_shared_messages=True,
                job_queue=self.client.job_queue
            )
            await update.effective_message.reply_text(
                f"You have aborted your most recent communism of "
                f"{self.client.format_balance(aborted_communism.amount)}!"
            )

        else:
            raise RuntimeError(f"Invalid communism subcommand detected, this shouldn't happen: {args.subcommand!r}")
