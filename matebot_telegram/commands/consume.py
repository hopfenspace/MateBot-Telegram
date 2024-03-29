"""
MateBot command executor classes for /consume
"""

import asyncio
from typing import List

import telegram.ext

from matebot_sdk import exceptions, schemas

from .. import client, err, util
from ..base import BaseCommand, BaseMessage
from ..parsing.types import natural as natural_type, extended_consumable_type
from ..parsing.util import Namespace


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


class ConsumeMessage(BaseMessage):
    """
    Handler for dynamic consume message commands, i.e. commands which are not statically registered
    """

    def __init__(self):
        super().__init__("consume")

    async def run(self, msg: telegram.Message, context: telegram.ext.CallbackContext) -> None:
        possible_consumable, possible_amount, *_ = msg.text.strip().split(" ") + ["1", ""]
        self.logger.debug(f"Incoming possible consume custom command. Text: '{msg.text}'")
        self.logger.debug(f"Consumable '{possible_consumable}' with amount '{possible_amount}'")

        possible_consumable = str(possible_consumable).split("@")[0]
        if possible_consumable.startswith("/"):
            possible_consumable = possible_consumable[1:]

        consumables = await self.client.get_consumables(name=possible_consumable)
        if len(consumables) != 1:
            msg.reply_text("Unknown command. See /help for details.")
            return

        try:
            amount = int(possible_amount)
        except ValueError:
            msg.reply_text("The specified amount doesn't look like it's a valid integer.")
            return
        if amount <= 0:
            msg.reply_text("The number of consumed goods must be positive.")
            return

        try:
            issuer = await self.client.get_core_user(msg.from_user)
            _ = await self.client.create_consumption(consumables[0], amount, issuer)
        except exceptions.MateBotSDKException as exc:
            msg.reply_text(exc.message)
        except err.MateBotException as exc:
            msg.reply_text(str(exc))
        else:
            msg.reply_text(
                f"Enjoy your{('', f' {amount}')[amount != 1]} {consumables[0].name}{('', 's')[amount != 1]}! "
                f"{consumables[0].emoji * amount}"
            )


def get_consumable_commands() -> List[telegram.BotCommand]:
    """
    Return a list of bot commands for the individual consumables
    """

    coroutine = client.client.get_consumables()
    consumables = asyncio.run_coroutine_threadsafe(coroutine, loop=util.event_loop).result()
    return [
        telegram.BotCommand(c.name, f"{c.description} ({client.client.format_balance(c.price)})")
        for c in consumables
    ]
