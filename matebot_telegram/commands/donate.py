"""
MateBot command executor classes for /donate and its callback queries
"""

import telegram
from matebot_sdk.exceptions import APIException

from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.types import amount_type
from ..parsing.util import Namespace


class DonateCommand(BaseCommand):
    """
    Command executor for /donate
    """

    def __init__(self):
        super().__init__(
            "donate",
            "Donate money to the community\n\n"
            "Performing this command allows you to transfer money to the "
            "community user. It works similar to the /send operation."
        )

        self.parser.add_argument("amount", type=amount_type)

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        msg = update.effective_message
        issuer = await self.client.get_core_user(msg.from_user)
        if issuer.privilege < issuer.privilege.VOUCHED:
            msg.reply_text("You are not permitted to use this feature. See /help for details.")
            return

        formatted_amount = self.client.format_balance(args.amount)
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton("CONFIRM", callback_data=f"donate confirm {args.amount} {msg.from_user.id}"),
            telegram.InlineKeyboardButton("ABORT", callback_data=f"donate abort {args.amount} {msg.from_user.id}")
        ]])
        msg.reply_text(f"Do you want to donate {formatted_amount} to the community?", reply_markup=keyboard)


class DonateCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /donate
    """

    def __init__(self):
        super().__init__("donate", "^donate", {
            "abort": self.abort,
            "confirm": self.confirm
        })

    async def confirm(self, update: telegram.Update) -> None:
        """
        Confirm and process a donation requests based on incoming callback queries

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        self.logger.debug("Confirming donation")
        _, amount, original_sender = self.data.split(" ")
        amount = int(amount)
        original_sender = int(original_sender)
        sender = await self.client.get_core_user(update.callback_query.from_user)
        receiver = await self.client.community

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer(f"Only the creator of this donation can confirm it!")
            return

        try:
            transaction = await self.client.create_transaction(sender, receiver, amount, "donation")
            update.callback_query.message.edit_text(
                f"Okay, you sent {self.client.format_balance(transaction.amount)} to the community!",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
        except APIException as exc:
            self.logger.warning(f"{type(exc).__name__}: {exc.message} ({exc.status}, {exc.details})")
            update.callback_query.edit_message_text(
                f"Your donation has been rejected. No money has been transferred:\n{exc.message}"
            )

    async def abort(self, update: telegram.Update) -> None:
        """
        Abort a donation requests

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        self.logger.debug("Aborting donation")
        _, _, original_sender = self.data.split(" ")
        original_sender = int(original_sender)

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer(f"Only the creator of this transaction can abort it!")
            return

        update.callback_query.message.edit_text(
            "You aborted the operation. No money has been donated.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
