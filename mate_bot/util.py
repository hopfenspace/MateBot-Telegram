"""
Collection of small MateBot utilities
"""

import logging as _logging
from typing import Any, Callable, Optional

import telegram


_logger = _logging.getLogger("error")


def safe_send(default: Callable[[], Any], fallback: Callable[[], Any], msg: Optional[str] = None) -> bool:
    """
    Safely send rich text messages to the Bot API, catching entity parsing problems

    This function is highly recommended wherever Markdown or HTML parsing is enabled.

    :param default: default callable that doesn't take any args and just delivers the message
    :param fallback: callable that doesn't take any args and will only be called when
        sending the message using the default callable failed with an entity parser error
    :param msg: optional message that was attempted to be sent, for inclusion in logs
    :return: whether the normal (default) message was delivered, or the fallback
    """

    try:
        default()
        return True
    except telegram.error.BadRequest as exc:
        if not str(exc).startswith("Can't parse entities"):
            raise
        _logger.error(f"Sending {msg!r} failed due to entity parsing problems: {exc!s}")
        fallback()
        _logger.debug("The message has been sent without formatting enabled (raw text).")
        return False
