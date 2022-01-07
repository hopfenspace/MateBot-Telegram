"""
Collection of parser argument types.
See :class:`mate_bot.parsing.actions.Action`'s type parameter
"""

import re
from typing import Union

import telegram

from .util import EntityString
from .. import registry, schemas, util
from ..base import BaseCommand
from ..client import SDK
from ..util import get_event_loop


__amount_pattern = re.compile(r"^(\d+)(?:[,.](\d)(\d)?)?$")
# Regex explanation:
# It matches any non-zero number of digits with an optional , or . followed by exactly one or two digits
# If there is a , or . then the first decimal is required
#
# The match's groups:
# 1st group: leading number, 2nd group: 1st decimal, 3rd group: 2nd decimal


def amount(arg: str) -> int:
    """
    Convert the string into an amount of money.

    :param arg: string to be parsed
    :type arg: str
    :return: Amount of money in cent
    :rtype: int
    :raises ValueError: when the arg seems to be no valid amount or is too big
    """

    match = __amount_pattern.match(arg)
    if match is None:
        raise ValueError("Doesn't match an amount's regex")

    val = int(match.group(1)) * 100
    if match.group(2):
        val += int(match.group(2)) * 10
    if match.group(3):
        val += int(match.group(3))

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
    return result


def user_type(arg: EntityString) -> schemas.User:
    """
    Convert an entity string into a User schema

    :param arg: string to be parsed
    :type arg: EntityString
    :return: fully functional MateBot User schema
    :rtype: matebot_sdk.schemas.User
    :raises ValueError: when username is ambiguous or the argument wasn't a mention
    """

    if arg.entity is None:
        raise ValueError('No user mentioned. Try with "@".')

    elif arg.entity.type in (telegram.constants.MESSAGEENTITY_MENTION, telegram.constants.MESSAGEENTITY_TEXT_MENTION):
        users = get_event_loop().run_until_complete(SDK.get_users_by_app_alias(str(arg)))
        if len(users) == 0:
            raise ValueError(
                "Ambiguous username. Make sure the username is correct and the "
                "user recently used the bot. Try sending /start to the bot privately."
            )
        if len(users) > 2:
            raise ValueError("Ambiguous username. Please ensure the users talked to the bot recently.")
        return users[0]

    else:
        raise ValueError('No user mentioned. Try with "@".')


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
        return registry.commands[arg.lower()]
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
    for consumable in util.get_consumables():
        if consumable.name.lower() == arg.lower():
            return consumable
    raise ValueError(f"{arg} is no known consumable")
