"""
MateBot command executor classes for /refund and its callback queries
"""

from typing import ClassVar

import telegram
from matebot_sdk import schemas

from .. import util
from ..base import BaseCallbackQuery, BaseCommand
from ..client import SDK
from ..parsing.actions import JoinAction
from ..parsing.types import amount as amount_type
from ..parsing.util import Namespace
from ..shared_messages import shared_message_handler


def _get_text(refund: schemas.Refund) -> str:
    return str(refund)  # TODO: heavily improve this!


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

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = util.get_event_loop().run_until_complete(
            SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
        )
        refunds = util.get_event_loop().run_until_complete(SDK.get_refunds_by_creator(user))
        active_refunds = [refund for refund in refunds if refund.active]
        if args.subcommand is None:
            if active_refunds:
                update.effective_message.reply_text(
                    f"You already have a {type(self).COMMAND_NAME} request in progress. Please handle it first."
                )
                return

            refund = util.get_event_loop().run_until_complete(SDK.make_new_refund(user, args.amount, args.reason))
            text = _get_text(refund)
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
            refund = util.get_event_loop().run_until_complete(SDK.cancel_refund(active_refunds[0]))
            text = _get_text(refund)
            keyboard = _get_keyboard(refund)
            util.update_all_shared_messages(
                update.effective_message.bot,
                "refund",
                refund.id,
                text,
                logger=self.logger,
                keyboard=keyboard
            )
            shared_message_handler.delete_messages("refund", refund.id)


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
                "disapprove": self.disapprove
            }
        )

    def approve(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        raise NotImplementedError

    def disapprove(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        raise NotImplementedError
