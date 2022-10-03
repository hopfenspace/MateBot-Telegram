"""
MateBot command executor classes for /consume
"""

import telegram
from matebot_sdk import schemas

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

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = await self.client.get_core_user(update.effective_message.from_user)
        amount = args.number
        consumable = args.consumable

        if isinstance(consumable, str) and consumable == "?":
            msg = await self.get_consumable_help()
            update.effective_message.reply_text(msg)

        elif isinstance(consumable, schemas.Consumable):
            consumption = await self.client.create_consumption(consumable, amount, sender)
            update.effective_message.reply_text(
                f"Enjoy your{('', f' {amount}')[amount != 1]} {consumable.name}{('', 's')[amount != 1]}! "
                f"You paid {self.client.format_balance(consumption.amount)} to the community."
            )

        else:
            raise RuntimeError(f"Invalid consumable: {consumable!r} {type(consumable)}")

    async def get_consumable_help(self) -> str:
        def make_line(c: schemas.Consumable) -> str:
            return f"- {c.name} (price {self.client.format_balance(c.price)}): {c.description}"

        lines = "\n".join([make_line(c) for c in await self.client.get_consumables()])
        return f"The following consumables are currently available:\n\n{lines}"
