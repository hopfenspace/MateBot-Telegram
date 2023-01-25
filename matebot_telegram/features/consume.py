"""
MateBot command executor class for /consume and the specialized consumption handler classes
"""

from typing import List

import telegram.ext
from matebot_sdk import schemas

from . import _app
from .base import BaseCommand, ExtendedContext, types, Namespace
from ..client import AsyncMateBotSDKForTelegram


class ConsumeCommand(BaseCommand):
    """
    Command executor for /consume
    """

    def __init__(self):
        super().__init__(
            "consume",
            "Consume consumable goods\n\n"
            "The first argument `consumable` determines which good you want to consume, "
            "while the optional second argument `number` determines the number of "
            "consumed goods (defaulting to a single one). Use the special consumable "
            "`?` to get a list of all available consumable goods currently available."
        )

        self.parser.add_argument("consumable", type=types.extended_consumable_type)
        self.parser.add_argument("number", default=1, type=types.natural, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: ExtendedContext
        :return: None
        """

        sender = await context.application.client.get_core_user(update.effective_message.from_user)
        amount = args.number
        consumable = args.consumable

        if isinstance(consumable, str) and consumable == "?":
            msg = await self.get_consumable_help(context)
            await update.effective_message.reply_text(msg)

        elif isinstance(consumable, schemas.Consumable):
            consumption = await context.application.client.create_consumption(consumable, amount, sender)
            await update.effective_message.reply_text(
                f"Enjoy your{('', f' {amount}')[amount != 1]} {consumable.name}{('', 's')[amount != 1]}! "
                f"You paid {context.application.client.format_balance(consumption.amount)} to the community."
            )

        else:
            raise RuntimeError(f"Invalid consumable: {consumable!r} {type(consumable)}")

    @staticmethod
    async def get_consumable_help(context: ExtendedContext) -> str:
        def make_line(c: schemas.Consumable) -> str:
            return f"- {c.name} (price {context.application.client.format_balance(c.price)}): {c.description}"

        lines = "\n".join([make_line(c) for c in await context.application.client.get_consumables()])
        return f"The following consumables are currently available:\n\n{lines}"


def build_consume_command(consumable: schemas.Consumable) -> BaseCommand:
    """
    Build a consume command handler class
    """

    class SpecificConsumptionCommand(BaseCommand):
        def __init__(self):
            super().__init__(
                consumable.name,
                f"{consumable.description} ({_app.client.format_balance(consumable.price)})"
            )
            self.parser.add_argument("number", default=1, type=types.natural, nargs="?")

        async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
            issuer = await context.application.client.get_core_user(update.effective_message.from_user)
            await context.application.client.create_consumption(consumable.name, args.number, issuer)
            await update.effective_message.reply_text(
                f"Enjoy your{('', f' {args.number}')[args.number != 1]} "
                f"{consumable.name}{('', 's')[args.number != 1]}! "
                f"{consumable.emoji * args.number}"
            )

    return type(f"{consumable.name.title()}ConsumptionCommand", (SpecificConsumptionCommand,), {})()


async def get_consumable_commands(client: AsyncMateBotSDKForTelegram) -> List[BaseCommand]:
    """
    Return a list of bot commands for the individual consumables
    """

    return [build_consume_command(c) for c in await client.get_consumables()]
