"""
MateBot command executor classes for /refund and its callback queries
"""

import time
from typing import Awaitable, Callable, ClassVar

import telegram
from matebot_sdk import exceptions, schemas

from . import _common
from .. import client, shared_messages, util
from ..api_callback import dispatcher
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.actions import JoinAction
from ..parsing.types import amount_type
from ..parsing.util import Namespace


async def _get_text(refund: schemas.Refund) -> str:
    approving = [vote.user_name for vote in refund.votes if vote.vote]
    disapproving = [vote.user_name for vote in refund.votes if not vote.vote]
    markdown = (
        f"*Refund by {refund.creator.name}*\n"
        f"Reason: {refund.description}\n"
        f"Amount: {client.client.format_balance(refund.amount)}\n"
        f"Created: {time.asctime(time.gmtime(refund.created))}\n\n"
        f"*Votes ({len(refund.votes)})*\n"
        f"Proponents ({len(approving)}): {', '.join(approving) or 'None'}\n"
        f"Opponents ({len(disapproving)}): {', '.join(disapproving) or 'None'}\n"
    )

    if refund.active:
        markdown += "\n_The refund request is currently active._"
    elif not refund.active:
        if refund.allowed is not None:
            markdown += f"\n_The request was {('rejected', 'allowed')[refund.allowed]}. "
        else:
            markdown += "\n_The request has been aborted. "
        if refund.transaction:
            markdown += f"The transaction has been processed. Take a look at your history for more details._"
        else:
            markdown += "No transactions have been processed._"
    return markdown


def _get_keyboard(refund: schemas.Refund) -> telegram.InlineKeyboardMarkup:
    if not refund.active:
        return telegram.InlineKeyboardMarkup([])
    return _common.get_voting_keyboard_for("refund", refund.id)


class RefundCommand(BaseCommand):
    """
    Command executor for /refund
    """

    # Set the actual command name (for the UI), since this class is subclassed as alias for /pay
    COMMAND_NAME: ClassVar[str] = "refund"

    def __init__(self):
        super().__init__(
            type(self).COMMAND_NAME,
            f"Use this command to create a {type(self).COMMAND_NAME} request.\n\n"
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
                _get_text,
                _get_keyboard,
                update.effective_message,
                shared_messages.ShareType.REFUND,
                self.logger
            )

        active_refunds = await self.client.get_refunds(active=True, creator_id=sender.id)
        if not active_refunds:
            update.effective_message.reply_text(f"You don't have a {type(self).COMMAND_NAME} request in progress.")
            return

        if len(active_refunds) > 1:
            update.effective_message.reply_text(
                f"You have more than one active {type(self).COMMAND_NAME} request. "
                f"The command will affect the most recent active {type(self).COMMAND_NAME} request."
            )

        if args.subcommand == "show":
            _common.show_updated_group_operation(
                self.client,
                update.effective_message,
                await _get_text(active_refunds[-1]),
                _get_keyboard(active_refunds[-1]),
                shared_messages.ShareType.REFUND,
                active_refunds[-1].id,
                self.logger
            )

        elif args.subcommand == "stop":
            aborted_refund = await self.client.abort_refund(active_refunds[-1], sender)
            text = await _get_text(aborted_refund)
            keyboard = _get_keyboard(aborted_refund)

            util.update_all_shared_messages(
                update.effective_message.bot,
                shared_messages.ShareType.REFUND,
                aborted_refund.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                delete_shared_messages=True
            )


class RefundCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /refund
    """

    def __init__(self):
        super().__init__(
            "refund",
            "^refund",
            {
                "approve": self.approve,
                "disapprove": self.disapprove,
                "abort": self.abort
            }
        )

    async def _handle_add_vote(
            self,
            update: telegram.Update,
            get_client_func: Callable[[int, schemas.User], Awaitable[schemas.RefundVoteResponse]]
    ) -> None:
        _, refund_id = self.data.split(" ")
        refund_id = int(refund_id)

        user = await self.client.get_core_user(update.callback_query.from_user)
        response = await get_client_func(refund_id, user)
        update.callback_query.answer(f"You successfully voted {('against', 'for')[response.vote.vote]} the request.")

        text = await _get_text(response.refund)
        keyboard = _get_keyboard(response.refund)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.REFUND,
            refund_id,
            text,
            logger=self.logger,
            keyboard=keyboard
        )

    async def approve(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_add_vote(update, self.client.approve_refund)

    async def disapprove(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_add_vote(update, self.client.disapprove_refund)

    async def abort(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, refund_id = self.data.split(" ")
        refund_id = int(refund_id)

        issuer = await self.client.get_core_user(update.callback_query.from_user)
        try:
            refund = await self.client.abort_refund(refund_id, issuer)
        except exceptions.APIException as exc:
            update.callback_query.answer(exc.message, show_alert=True)
            return

        text = await _get_text(refund)
        keyboard = _get_keyboard(refund)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.REFUND,
            refund.id,
            text,
            logger=self.logger,
            keyboard=keyboard,
            delete_shared_messages=True,
            job_queue=self.client.job_queue
        )
        update.callback_query.answer()


@dispatcher.register_for(schemas.EventType.REFUND_CREATED)
async def _handle_refund_created(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await client.client.get_refunds(id=refund_id))[0]
    util.send_auto_share_messages(
        client.client.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await _get_text(refund),
        keyboard=_get_keyboard(refund),
        job_queue=client.client.job_queue
    )


@dispatcher.register_for(schemas.EventType.REFUND_UPDATED)
async def _handle_refund_updated(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await client.client.get_refunds(id=refund_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await _get_text(refund),
        keyboard=_get_keyboard(refund),
        job_queue=client.client.job_queue
    )


@dispatcher.register_for(schemas.EventType.REFUND_CLOSED)
async def _handle_refund_closed(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await client.client.get_refunds(id=refund_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await _get_text(refund),
        keyboard=_get_keyboard(refund),
        delete_shared_messages=True,
        job_queue=client.client.job_queue
    )
