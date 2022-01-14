"""
MateBot command executor classes for /send and its callback queries
"""

import telegram
from matebot_sdk.base import PermissionLevel
from matebot_sdk.exceptions import UserAPIException

from .. import util
from ..base import BaseCallbackQuery, BaseCommand
from ..client import SDK
from ..parsing.types import amount as amount_type
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

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = util.get_event_loop().run_until_complete(
            SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
        )
        permission_check = SDK.ensure_permissions(sender, PermissionLevel.ANY_WITH_VOUCHER, "send")
        if not permission_check[0]:
            update.effective_message.reply_text(permission_check[1])
            return
        if not args.receiver:
            update.effective_message.reply_text("The receiver was not found on the server!")
            return
        if args.receiver.id == sender.id:
            update.effective_message.reply_text("You can't send money to yourself.")
            return

        if isinstance(args.reason, list):
            reason = "send: " + " ".join(map(str, args.reason))
        else:
            reason = "send: " + str(args.reason)

        def e(variant: str) -> str:
            return f"send {variant} {args.amount} {update.effective_message.from_user.id} {args.receiver.id}"

        msg = f"Do you want to send {args.amount / 100 :.2f}€ to {args.receiver.name}?\nDescription: `{reason}`"
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton("CONFIRM", callback_data=e("confirm")),
            telegram.InlineKeyboardButton("ABORT", callback_data=e("abort"))
        ]])
        util.safe_call(
            lambda: update.effective_message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown"),
            lambda: update.effective_message.reply_text(
                "The request can't be processed, since the message contains "
                "forbidden entities, e.g. underscores or apostrophes."
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

    def confirm(self, update: telegram.Update) -> None:
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
        receiver_id = int(receiver_id)

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer(f"Only the creator of this transaction can confirm it!")
            return

        sender = util.get_event_loop().run_until_complete(SDK.get_user_by_app_alias(str(original_sender)))
        receiver = util.get_event_loop().run_until_complete(SDK.get_user_by_id(receiver_id))

        reason = None
        for entity in update.callback_query.message.parse_entities():
            if entity.type == "code":
                if reason is None:
                    reason = update.callback_query.message.parse_entity(entity)
                else:
                    raise RuntimeError("Multiple reason definitions")

        if reason is None:
            raise RuntimeError("Unknown reason while confirming a Transaction")

        try:
            transaction = util.get_event_loop().run_until_complete(
                SDK.make_new_transaction(sender, receiver, amount, reason)
            )
            update.callback_query.message.edit_text(
                f"Okay, you sent {transaction.amount / 100 :.2f}€ to {SDK.get_username(receiver)}",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
        except UserAPIException as exc:
            self.logger.warning(f"{type(exc).__name__}: {exc.message} ({exc.status}, {exc.details})")
            update.callback_query.edit_message_text(
                f"Your request couldn't be processed. No money has been transferred:\n{exc.message}"
            )

    def abort(self, update: telegram.Update) -> None:
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
