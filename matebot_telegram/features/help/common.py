"""
Common utilities for the help feature
"""

from typing import Optional

from matebot_sdk.schemas import User

from ..commands.command import BaseCommand
from ...client import AsyncMateBotSDKForTelegram


async def get_help_usage(usage: str, client: AsyncMateBotSDKForTelegram, issuer: Optional[User] = None) -> str:
    """
    Retrieve the help message from the help command without arguments

    :param usage: usage string of the help command
    :param client: the async SDK client for telegram
    :param issuer: optional User who issued the help command
    :return: fully formatted help message when invoking the help command without arguments
    """

    command_list = "\n".join(map(lambda c: f" - `{c}`", sorted(BaseCommand.AVAILABLE_COMMANDS.keys())))
    msg = f"*MateBot Telegram help page*\n\nUsage of this command: `{usage}`\n\nList of commands:\n{command_list}"
    dynamic_commands = "\n".join(sorted(
        [f"- `{c.name}` for {client.format_balance(c.price)}" for c in
         await client.get_consumables()]
    ))
    msg += f"\n\nAdditionally, the following dynamic consumption commands are available:\n{dynamic_commands}"

    if issuer and not issuer.active:
        msg += "\n\nYour user account has been disabled. You're not allowed to interact with the bot."

    elif issuer and issuer.external:
        msg += "\n\nYou are an external user. Some commands may be restricted."

        if issuer.voucher_id is None:
            msg += (
                "\nYou don't have any creditor. Your possible interactions "
                "with the bot are very limited for security purposes. You "
                "can ask some internal user to act as your voucher. To "
                "do this, the internal user needs to execute `/vouch "
                "<your username>`. Afterwards, you may use this bot.\n"
                "Alternatively, use the /poll command to request access "
                "to the internal group by community approval."
            )

    elif issuer and issuer.privilege >= issuer.privilege.PERMITTED:
        msg += "\n\nYou have been granted extended voting permissions. With great power comes great responsibility."

    return msg


def get_help_for_command(command: BaseCommand) -> str:
    """
    Get the help message for a specific command in Markdown

    :param command: command which should be used for help message generation
    :return: Markdown-enabled help message for a specific command
    """

    usages = "\n".join(map(lambda x: f"`/{command.name} {x}`", command.parser.usages))
    return f"*Usages:*\n{usages}\n\n*Description:*\n{command.description}"
