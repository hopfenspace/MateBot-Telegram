"""
MateBot command executor classes for /consume
"""

import random

import telegram

from .. import config, connector, schemas, util
from ..base import BaseCommand
from ..parsing.types import natural as natural_type, extended_consumable_type
from ..parsing.util import Namespace


class ConsumeCommand(BaseCommand):
    """
    Command executor for /consume
    """

    def __init__(self):
        super().__init__(
            "consume",
            "Use this command to consume consumable goods.\n\n"
            "The first argument `consumable` determines which good you want to consume, "
            "while the optional second argument `number` determines the number of "
            "consumed goods (defaulting to a single one). Use the special consumable "
            "`?` to get a list of all available consumable goods currently available."
        )

        self.parser.add_argument("consumable", type=extended_consumable_type)
        self.parser.add_argument("number", default=1, type=natural_type, nargs="?")

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

        user = util.get_user_by(update.effective_message.from_user, update.effective_message.reply_text, connect)
        if user is None:
            return
        if not util.ensure_permissions(
                user, util.PermissionLevel.ANY_WITH_VOUCHER, update.effective_message, "consume"
        ):
            return

        consumable = args.consumable

        if isinstance(consumable, str) and consumable == "?":
            msg = self.get_consumable_help()
            util.safe_call(
                lambda: update.effective_message.reply_markdown(msg),
                lambda: update.effective_message.reply_text(msg)
            )
            return

        elif isinstance(consumable, schemas.Consumable):
            consumption = {
                "user": user.id,
                "amount": args.number,
                "consumable_id": consumable.id,
                "adjust_stock": config.config["respect-stock"],
                "respect_stock": config.config["respect-stock"]
            }

            response = connect.post("/v1/transactions", json_obj=consumption)
            if response.ok:
                schemas.Transaction(**response.json())
                msg = random.choice(consumable.messages) + consumable.symbol * args.number
                util.safe_call(
                    lambda: update.effective_message.reply_markdown(msg),
                    lambda: update.effective_message.reply_text(msg)
                )
            else:
                update.effective_message.reply_text("Something failed. You didn't consume any goods!")
                raise RuntimeError(f"Consumption failed. HTTP {response.status_code}: {response.content}")
            return

        raise RuntimeError(f"Invalid consumable: {consumable!r} {type(consumable)}")

    @staticmethod
    def get_consumable_help(connect: connector.APIConnector = None) -> str:
        # TODO: improve the line of text generated by this function
        def make_line(c: schemas.Consumable) -> str:
            return f"{c.symbol} {c.name} (price {c.price/100:.2f}€): {c.description} (stock: {c.stock})"

        lines = "\n".join([make_line(c) for c in util.get_consumables(connect)])
        return f"The following consumables are currently available:\n\n{lines}"
