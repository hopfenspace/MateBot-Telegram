import logging
from typing import Any, Callable, Union

import telegram

from . import connector, schemas


def safe_send(bot: telegram.Bot, chat_id: Union[int, str], default: str, fallback: str, *args, **kwargs) -> bool:
    try:
        bot.send_message(chat_id, default, *args, **kwargs)
        return True
    except telegram.error.BadRequest as exc:
        if not str(exc).startswith("Can't parse entities"):
            raise
        logger = kwargs.get("logger") or logging.getLogger(__name__)
        logger.exception(f"Sending {default!r} failed due to entity parsing problems: {exc!s}")
        bot.send_message(chat_id, fallback, *args, **kwargs)
        logger.debug("The message has been sent without formatting enabled (raw text).")
        return False


def safe_call(default: Callable[[], Any], fallback: Callable[[], Any],logger: logging.Logger = None) -> bool:
    try:
        default()
        return True
    except telegram.error.BadRequest as exc:
        if not str(exc).startswith("Can't parse entities"):
            raise
        logger = logger or logging.getLogger(__name__)
        logger.exception(f"Calling sender function {default} failed due to entity parsing problems: {exc!s}")
        fallback()
        logger.debug(f"Calling fallback function {fallback} was successful instead.")
        return False


def get_alias_by_telegram_id(telegram_id: int, connect: connector.APIConnector = None) -> schemas.Alias:
    connect = connect or connector.connector
    response = connect.get(f"/v1/aliases/application/{connect.app_name}")
    if not response.ok:
        raise RuntimeError  # TODO: implement better exception handling
    hits = [e for e in response.json() if e["app_user_id"] == str(telegram_id)]
    if len(hits) == 0:
        raise NotImplementedError  # TODO: probably 404 -> implement starting procedure
    return schemas.Alias(**hits[0])


def get_user_by_telegram_id(telegram_id: int, connect: connector.APIConnector = None) -> schemas.User:
    connect = connect or connector.connector
    alias = get_alias_by_telegram_id(telegram_id, connect)
    response = connect.get(f"/v1/users/{alias.user_id}")
    if not response.ok:
        raise NotImplementedError  # TODO: probably 404 -> implement starting procedure
    return schemas.User(**response.json())


def handle_unknown_user():
    raise NotImplementedError
