"""
MateBot command executor classes for /send and its callback queries
"""

import telegram
from matebot_sdk.exceptions import APIException

from .. import util
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.types import amount_type
from ..parsing.types import user_type
from ..parsing.util import Namespace


class SendCommand(BaseCommand):
    """
    Command executor for /send
    """

    def __init__(self):
        super().__init__(
            "send",
            "Use this command to send money to another user.\n\n"
            "Performing this command allows you to send money to someone else. "
            "Obviously, the receiver of your transaction has to be registered with "
            "this bot. For security purposes, the bot will ask you to confirm your "
            "proposed transaction before the virtual money will be transferred.\n\n"
            "The first and second argument, `amount` and `receiver` respectively, are "
            "mandatory. But you can add as many extra words as you want afterwards. "
            "Those are treated as description/reason for your transaction."
        )

        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("receiver", type=user_type)
        self.parser.add_argument("reason", default="<no description>", nargs="*")
        second_usage = self.parser.new_usage()
        second_usage.add_argument("receiver", type=user_type)
        second_usage.add_argument("amount", type=amount_type)
        second_usage.add_argument("reason", default="<no description>", nargs="*")

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if isinstance(args.reason or [], list):
            reason = "send: " + " ".join(map(str, args.reason))
        else:
            reason = "send: " + str(args.reason)

        issuer = await self.client.get_core_user(update.effective_message.from_user)
        if issuer.privilege < issuer.privilege.VOUCHED:
            update.effective_message.reply_text("You are not permitted to use this feature. See /help for details.")
            return

        def e(variant: str) -> str:
            return f"send {variant} {args.amount} {update.effective_message.from_user.id} {args.receiver.id}"

        formatted_amount = self.client.format_balance(args.amount)
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton("CONFIRM", callback_data=e("confirm")),
            telegram.InlineKeyboardButton("ABORT", callback_data=e("abort"))
        ]])
        util.safe_call(
            lambda: update.effective_message.reply_markdown(
                f"Do you want to send {formatted_amount} to {args.receiver.name}?\nDescription: `{reason}`",
                reply_markup=keyboard
            ),
            lambda: update.effective_message.reply_text(
                f"Do you want to send {formatted_amount} to {args.receiver.name}?\n\n"
                f"Attention: Since your description contains forbidden characters like underscores "
                f"or apostrophes, the description '<no reason>' will be used as a fallback value.",
                reply_markup=keyboard
            )
        )


class SendCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /send
    """

    def __init__(self):
        super().__init__("send", "^send", {
            "abort": self.abort,
            "confirm": self.confirm
        })

    async def confirm(self, update: telegram.Update) -> None:
        """
        Confirm and process an transaction requests based on incoming callback queries

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        self.logger.debug("Confirming transaction")
        _, amount, original_sender, receiver_id = self.data.split(" ")
        amount = int(amount)
        original_sender = int(original_sender)
        sender = await self.client.get_core_user(update.callback_query.from_user)
        receiver = await self.client.get_user(int(receiver_id))

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer(f"Only the creator of this transaction can confirm it!")
            return

        reason = None
        for entity in update.callback_query.message.parse_entities():
            if entity.type == telegram.MessageEntity.CODE:
                if reason is None:
                    reason = update.callback_query.message.parse_entity(entity)
                else:
                    raise RuntimeError("Multiple reason definitions")

        if reason is None:
            reason = "send: <no description>"
            self.logger.error("No description provided")

        try:
            transaction = await self.client.create_transaction(sender, receiver, amount, reason)
            update.callback_query.message.edit_text(
                f"Okay, you sent {self.client.format_balance(transaction.amount)} to {receiver.name}!",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
        except APIException as exc:
            self.logger.warning(f"{type(exc).__name__}: {exc.message} ({exc.status}, {exc.details})")
            update.callback_query.edit_message_text(
                f"Your request has been rejected. No money has been transferred:\n{exc.message}"
            )

    async def abort(self, update: telegram.Update) -> None:
        """
        Abort an transaction requests

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        self.logger.debug("Aborting transaction")
        _, _, original_sender, _ = self.data.split(" ")
        original_sender = int(original_sender)

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer(f"Only the creator of this transaction can abort it!")
            return

        update.callback_query.message.edit_text(
            "You aborted the operation. No money has been sent.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
