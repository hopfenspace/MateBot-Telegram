"""
MateBot command executor class for /communism
"""

import telegram.ext

from . import common
from ..base import BaseCommand, ExtendedContext, Namespace, types
from .. import _common  # TODO: Drop this import in favor of a restructured handler function
from ... import shared_messages
from ...parsing.actions import JoinAction


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

        self.parser.add_argument("amount", type=types.amount_type)
        self.parser.add_argument("reason", nargs="+", action=JoinAction)

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        Create a new communism with the supplied arguments, providing a message with attached inline keyboard
        """

        user = await context.application.client.get_core_user(update.effective_message.from_user)

        if args.subcommand is None:
            return await _common.new_group_operation(
                context.application.client.create_communism(user, args.amount, args.reason),
                context.application.client,
                lambda c: common.get_text(context.application.client, c),
                common.get_keyboard,
                update.effective_message,
                shared_messages.ShareType.COMMUNISM,
                self.logger
            )

        active_communisms = await context.application.client.get_communisms(active=True, creator_id=user.id)
        if not active_communisms:
            await update.effective_message.reply_text("You don't have a communism in progress.")
            return

        if args.subcommand == "show":
            await _common.show_updated_group_operation(
                context.application.client,
                update.effective_message,
                await common.get_text(context.application.client, active_communisms[-1]),
                common.get_keyboard(active_communisms[-1]),
                shared_messages.ShareType.COMMUNISM,
                active_communisms[-1].id,
                self.logger
            )

        elif args.subcommand == "stop":
            aborted_communism = await context.application.client.abort_communism(active_communisms[-1], user)
            text = await common.get_text(context.application.client, aborted_communism)
            keyboard = common.get_keyboard(aborted_communism)

            await context.application.update_shared_messages(
                shared_messages.ShareType.COMMUNISM,
                aborted_communism.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                delete_shared_messages=True,
                job_queue=True
            )
            await update.effective_message.reply_text(
                f"You have aborted your most recent communism of "
                f"{context.application.client.format_balance(aborted_communism.amount)}!"
            )

        else:
            raise RuntimeError(f"Invalid communism subcommand detected, this shouldn't happen: {args.subcommand!r}")
