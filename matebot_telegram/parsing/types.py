"""
Collection of parser argument types.
See :class:`mate_bot.parsing.actions.Action`'s type parameter
"""

import re
import asyncio
from typing import Union

import telegram
from matebot_sdk import schemas

from .util import EntityString
from .. import client, config, err, util
from ..base import BaseCommand


def amount_type(arg: str) -> int:
    """
    Convert the string into an amount of money

    See :func:`amount` for more details.
    """

    value = amount(arg, config.config.currency.digits)
    if value >= 2**31:
        raise ValueError("Integer too large!")
    return value


def amount(arg: str, digits: int) -> int:
    """
    Convert the string into an amount of money

    Explanation of the regular expression ``amount_pattern``:
    It matches any non-zero number of digits with an optional comma ``,``
    or dot ``.`` followed by a configured maximum number of digits.
    If there is a ``,`` or ``.`` then the first decimal is required.
    The first group of a match is are leading digits before a dot or comma,
    while every following group is a single digit after the dot or comma.

    :param arg: string to be parsed
    :type arg: str
    :param digits: number of digits behind the separation symbol usually used
        in expressions of the amount in the currency (e.g. ``13.37€`` is a
        usual expression for an amount in Euros with two digits behind the dot)
    :type digits: int
    :return: Amount of money in cent
    :rtype: int
    :raises ValueError: when the arg seems to be no valid amount or is too big
    """

    if digits == 0:
        amount_pattern = re.compile(r"^(\d+)$")
    elif digits > 0:
        amount_pattern = re.compile(r"^(\d+)(?:[,.](\d)" + r"(\d)?" * (digits - 1) + r")?$")
    else:
        raise ValueError("Negative number of digits is invalid")

    match = amount_pattern.match(arg)
    if match is None:
        raise ValueError("Doesn't match an amount's regex")

    val = sum(int(v or 0) * 10**i for i, v in list(enumerate(reversed(match.groups()))))
    if val == 0:
        raise ValueError("An amount can't be zero")
    return val


def natural(arg: str) -> int:
    """
    Convert the string into a natural number (positive integer)

    :param arg: string to be parsed
    :type arg: str
    :return: only positive integers
    :rtype: int
    :raises ValueError: when the string seems to be no integer or is not positive
    """

    result = int(arg)
    if result <= 0:
        raise ValueError("Not a positive integer.")
    if result >= 2**31:
        raise ValueError("Integer too large.")
    return result


def _conv_arg_to_user(arg: EntityString, allow_foreign_user: bool) -> schemas.User:
    if arg.entity and arg.entity.type == telegram.constants.MESSAGEENTITY_TEXT_MENTION:
        coroutine = client.client.get_core_user(arg.entity.user, foreign_user=allow_foreign_user)
    elif arg.entity is None or arg.entity.type == telegram.constants.MESSAGEENTITY_MENTION:
        coroutine = client.client.get_core_user(str(arg), foreign_user=allow_foreign_user)
    else:
        raise err.ParsingError('No user mentioned. Try with "@".')
    return asyncio.run_coroutine_threadsafe(coroutine, loop=util.event_loop).result()


def user_type(arg: EntityString) -> schemas.User:
    """
    Convert an entity string into a User schema

    :param arg: string to be parsed
    :type arg: EntityString
    :return: fully functional MateBot User schema
    :rtype: matebot_sdk.schemas.User
    :raises ValueError: when username is ambiguous or the argument wasn't a mention
    """

    return _conv_arg_to_user(arg, False)


def any_user_type(arg: EntityString) -> schemas.User:
    """
    Convert an entity string into a User schema, allowing foreign users that never used this application

    :param arg: string to be parsed
    :type arg: EntityString
    :return: fully functional MateBot User schema
    :rtype: matebot_sdk.schemas.User
    :raises ValueError: when username is ambiguous or the argument wasn't a mention
    """

    return _conv_arg_to_user(arg, True)


def command(arg: str) -> BaseCommand:
    """
    Convert the string into a command with this name

    :param arg: the desired command's name
    :type arg: str
    :return: the command
    :rtype: BaseCommand
    :raises ValueError: when the command is unknown
    """

    try:
        return BaseCommand.AVAILABLE_COMMANDS[arg.lower()]
    except KeyError:
        raise ValueError(f"{arg} is an unknown command")


def extended_consumable_type(arg: str) -> Union[schemas.Consumable, str]:
    """
    Convert the string into a consumable schema, if found, or the special string "?"

    :param arg: the desired consumable's name
    :type arg: str
    :return: the found consumable schema or the fixed special string "?"
    :rtype: Union[matebot_telegram.schemas.Consumable, str]
    :raises ValueError: when the consumable wasn't found or the string isn't "?"
    """

    if arg.strip() == "?":
        return "?"
    for consumable in asyncio.run_coroutine_threadsafe(client.client.get_consumables(), loop=util.event_loop).result():
        if consumable.name.lower() == arg.lower():
            return consumable
    raise ValueError(f"{arg} is no known consumable")
