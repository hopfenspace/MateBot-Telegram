"""
MateBot command executor classes for /send
"""

import telegram

from .. import connector, schemas, util
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.types import amount as amount_type
from ..parsing.types import user as user_type
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

    def run(self, args: Namespace, update: telegram.Update, connect: connector.APIConnector) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        sender = util.get_user_by(update.effective_message.from_user, update.effective_message.reply_text, connect)
        if sender is None:
            return
        if not util.ensure_permissions(sender, util.PermissionLevel.ANY_WITH_VOUCHER, update.effective_message, "send"):
            return
        if not args.receiver:
            update.effective_message.reply_text("The receiver was not found on the server!")
            return

        if isinstance(args.reason, list):
            reason = "send: " + " ".join(map(str, args.reason))
        else:
            reason = "send: " + args.reason

        def e(variant: str) -> str:
            return f"send {variant} {args.amount} {sender.id} {args.receiver.id}"

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
        super().__init__("send", "^send")

    def run(self, update: telegram.Update, connect: connector.APIConnector) -> None:
        """
        Process or abort transaction requests based on incoming callback queries

        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        try:
            variant, amount, original_sender, receiver_id = self.data.split(" ")
            amount = int(amount)
            receiver_id = int(receiver_id)
            original_sender = int(original_sender)

            if variant == "confirm":
                confirmation = True
            elif variant == "abort":
                confirmation = False
            else:
                raise ValueError(f"Invalid confirmation setting: '{variant}'")

            sender = util.get_user_by(update.callback_query.from_user, update.callback_query.answer, connect)
            if sender is None:
                return
            if sender.id != original_sender:
                update.callback_query.answer(f"Only the creator of this transaction can {variant} it!")
                return

            fake_receiver = object()
            fake_receiver.id = receiver_id
            fake_receiver.name = "<unknown>"
            receiver = util.get_user_by(fake_receiver, update.callback_query.answer, connect)  # noqa
            if receiver is None:
                return

            reason = None
            for entity in update.callback_query.message.parse_entities():
                if entity.type == "code":
                    if reason is None:
                        reason = update.callback_query.message.parse_entity(entity)
                    else:
                        raise RuntimeError("Multiple reason definitions")

            if reason is None:
                raise RuntimeError("Unknown reason while confirming a Transaction")

            if confirmation:
                response = connect.post("/v1/transactions", json_obj={
                    "sender": sender.id,
                    "receiver": receiver.id,
                    "amount": amount,
                    "reason": reason
                })

                if response.ok:
                    transaction = schemas.Transaction(**response.json())
                    update.callback_query.message.edit_text(
                        f"Okay, you sent {transaction.amount / 100 :.2f}€ to {receiver.name}",
                        reply_markup=telegram.InlineKeyboardMarkup([])
                    )
                else:
                    update.callback_query.message.edit_text(
                        "Your request couldn't be processed. No money has been transferred.\n"
                        f"Extra information: `Error {response.status_code}`\n\n`{response.json()}`",
                        reply_markup=telegram.InlineKeyboardMarkup([])
                    )

            else:
                update.callback_query.message.edit_text(
                    "You aborted the operation. No money has been sent.",
                    reply_markup=telegram.InlineKeyboardMarkup([])
                )

        except (IndexError, ValueError, TypeError, RuntimeError):
            update.callback_query.message.edit_text(
                "There was an error processing this request. No money has been sent.",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
            raise
