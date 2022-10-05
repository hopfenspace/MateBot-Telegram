"""
MateBot command executor classes for /refund and its callback queries
"""

import logging
from typing import Callable, ClassVar, Coroutine

import telegram
from matebot_sdk import schemas

from .. import util
from ..api_callback import dispatcher
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.actions import JoinAction
from ..parsing.types import amount as amount_type
from ..parsing.util import Namespace


async def _get_text(refund: schemas.Refund) -> str:
    users = await self.client.get_users()

    def get_username(vote: schemas.Vote) -> str:
        user = [u for u in users if u.id == vote.user_id]
        if len(user) != 1:
            raise ValueError(f"User ID {vote.user_id} couldn't be converted to username properly.")
        return self.client.get_username(user[0])

    approving = [get_username(vote) for vote in refund.poll.votes if vote.vote == 1]
    neutral = [get_username(vote) for vote in refund.poll.votes if vote.vote == 0]
    disapproving = [get_username(vote) for vote in refund.poll.votes if vote.vote == -1]
    markdown = (
        f"*Refund by {self.client.get_username(refund.creator)}*\n"
        f"Reason: {refund.description}\n"
        f"Amount: {refund.amount / 100 :.2f}€\n\n"
        f"*Votes ({len(refund.poll.votes)})*\n"
        f"Proponents ({len(approving)}): {', '.join(approving)}\n"
        f"Opposers ({len(disapproving)}): {', '.join(disapproving)}\n"
        + (f"Neutral ({len(neutral)}): {', '.join(neutral)}\n" if neutral else "")
    )

    if refund.active:
        markdown += "\n_The refund request is currently active._"
    elif not refund.active:
        markdown += "\n_The refund request has been closed._"
        if refund.transaction:
            markdown += f"\nThe transaction has been processed. Take a look at /history for more details."
        else:
            markdown += "\nThe refund request was denied or cancelled. No transactions have been processed."

    return markdown


def _get_keyboard(refund: schemas.Refund) -> telegram.InlineKeyboardMarkup:
    if not refund.active:
        return telegram.InlineKeyboardMarkup([])

    return telegram.InlineKeyboardMarkup([
        [
            telegram.InlineKeyboardButton("APPROVE", callback_data=f"refund approve {refund.id}"),
            telegram.InlineKeyboardButton("DISAPPROVE", callback_data=f"refund disapprove {refund.id}"),
        ],
        [
            telegram.InlineKeyboardButton("FORWARD", switch_inline_query_current_chat=f"{refund.id} "),
            telegram.InlineKeyboardButton("CLOSE", callback_data=f"refund close {refund.id}")
        ]
    ])


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

        user = await self.client.get_user_by_app_alias(str(update.effective_message.from_user.id))
        refunds = await self.client.get_refunds_by_creator(user)
        active_refunds = [refund for refund in refunds if refund.active]
        if args.subcommand is None:
            if active_refunds:
                update.effective_message.reply_text(
                    f"You already have a {type(self).COMMAND_NAME} request in progress. Please handle it first."
                )
                return

            refund = await self.client.make_new_refund(user, args.amount, args.reason)
            text = await _get_text(refund)
            keyboard = _get_keyboard(refund)
            message: telegram.Message = util.safe_call(
                lambda: update.effective_message.reply_markdown(text, reply_markup=keyboard),
                lambda: update.effective_message.reply_text(text, reply_markup=keyboard),
                use_result=True
            )
            shared_message_handler.add_message_by("refund", refund.id, message.chat_id, message.message_id)
            util.send_auto_share_messages(
                update.effective_message.bot,
                "refund",
                refund.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                excluded=[message.chat_id]
            )
            return

        if not active_refunds:
            update.effective_message.reply_text(f"You don't have a {type(self).COMMAND_NAME} request in progress.")
            return

        if len(active_refunds) > 1:
            update.effective_message.reply_text(
                f"You have more than one active {type(self).COMMAND_NAME} request. "
                f"The subcommand will use the oldest active {type(self).COMMAND_NAME} request."
            )

        if args.subcommand == "show":
            # TODO: implement showing the currently active refund in the current chat & updating the shared messages
            update.effective_message.reply_text("Not implemented.")

        elif args.subcommand == "stop":
            refund = await self.client.cancel_refund(active_refunds[0])
            text = await _get_text(refund)
            keyboard = _get_keyboard(refund)
            util.update_all_shared_messages(
                update.effective_message.bot,
                "refund",
                refund.id,
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
                "close": self.close
            }
        )

    async def _handle_add_vote(
            self,
            update: telegram.Update,
            get_client_func: Callable[[int, schemas.User], Coroutine]
    ) -> None:
        _, refund_id = self.data.split(" ")
        refund_id = int(refund_id)

        user = await self.client.get_user_by_app_alias(str(update.callback_query.from_user.id))
        vote = await get_client_func(refund_id, user)
        update.callback_query.answer(f"You successfully voted {('against', 'for')[vote.vote]} the request.")

        refund = await self.client.get_refund_by_id(refund_id)
        text = await _get_text(refund)
        keyboard = _get_keyboard(refund)
        util.update_all_shared_messages(
            update.callback_query.bot,
            "refund",
            refund.id,
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

    async def close(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, refund_id = self.data.split(" ")
        refund_id = int(refund_id)

        refund = await self.client.get_refund_by_id(refund_id)
        user = await self.client.get_user_by_app_alias(str(update.callback_query.from_user.id))
        if refund.creator.id != user.id:
            update.callback_query.answer(f"Only the creator of this refund can close it!")
            return

        refund = await self.client.cancel_refund(refund)
        text = await _get_text(refund)
        keyboard = _get_keyboard(refund)
        util.update_all_shared_messages(
            update.callback_query.bot,
            "refund",
            refund.id,
            text,
            logger=self.logger,
            keyboard=keyboard,
            delete_shared_messages=True
        )


async def _refund_callback_handler(method, _: str, id_: int, bot: telegram.Bot, logger: logging.Logger):
    # refund = await self.client.get_refund_by_id(id_)
    # if method == method.CREATE:
    #     util.send_auto_share_messages(bot, "refund", id_, await _get_text(refund), logger, _get_keyboard(refund))
    # elif method == method.UPDATE or method == method.DELETE:
    #     util.update_all_shared_messages(bot, "refund", id_, await _get_text(refund), logger, _get_keyboard(refund))
    #     if method == method.DELETE:
    #         shared_message_handler.delete_messages("refund", refund.id)
    pass


@dispatcher.register_for(schemas.EventType.REFUND_CREATED)
async def _handle_refund_created(event: schemas.Event):
    raise NotImplementedError


@dispatcher.register_for(schemas.EventType.REFUND_UPDATED)
async def _handle_refund_updated(event: schemas.Event):
    raise NotImplementedError


@dispatcher.register_for(schemas.EventType.REFUND_CLOSED)
async def _handle_refund_closed(event: schemas.Event):
    raise NotImplementedError
