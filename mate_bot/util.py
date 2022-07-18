"""
Collection of small MateBot utilities
"""

import logging as _logging
from typing import Any, Callable, Optional

import telegram

from . import config as _config

_logger = _logging.getLogger("error")


def safe_send(
        default: Callable[[], Any],
        fallback: Callable[[], Any],
        msg: Optional[str] = None,
        obj: bool = True,
) -> Any:
    """
    Safely send rich text messages to the Bot API, catching entity parsing problems

    This function is highly recommended wherever Markdown or HTML parsing is enabled.

    :param default: default callable that doesn't take any args and just delivers the message
    :param fallback: callable that doesn't take any args and will only be called when
        sending the message using the default callable failed with an entity parser error
    :param msg: optional message that was attempted to be sent, for inclusion in logs
    :param obj: switch to enable returning the result of the function (otherwise, determines
        the executed function using True for default or False for fallback instead)
    :return: whether the normal (default) message was delivered, or the fallback
    """

    try:
        default_obj = default()
        return default_obj if obj else True
    except telegram.error.BadRequest as exc:
        if not str(exc).startswith("Can't parse entities"):
            raise
        _logger.error(f"Sending {msg!r} failed due to entity parsing problems: {exc!s}")
        fallback_obj = fallback()
        _logger.debug("The message has been sent without formatting enabled (raw text).")
        return fallback_obj if obj else False


def format_currency(amount: int) -> str:
    """
    Format the given amount in the configured currency and factor
    """

    value = amount / _config.config['currency']['factor']
    return f"{value : .2f}{_config.config['currency']['symbol']}"
