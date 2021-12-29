import sys
import json
import logging
import traceback
from typing import Any, Callable, Union

import requests
import telegram.ext

from . import config, connector, schemas


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


def safe_call(default: Callable[[], Any], fallback: Callable[[], Any], logger: logging.Logger = None) -> bool:
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


def log_error(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """
    Log any error and its traceback to sys.stdout and send it to developers

    :param update: Telegram Update where the error probably occurred
    :type update: telegram.Update
    :param context: context of the error
    :type context: telegram.ext.CallbackContext
    :return: None
    """

    logger = logging.getLogger("error")
    if update is None:
        logger.warning("Error handler called without Update object. Check for network/connection errors!")
        token = config.config["token"]
        response = requests.get(f"https://api.telegram.org/bot{token}/getme")
        if response.status_code != 200:
            logger.error("Network check failed. Telegram API seems to be unreachable.")
        else:
            logger.debug("Network check succeeded. Telegram API seems to be reachable.")

    if not any(sys.exc_info()):
        logger.error("Error handler called without an exception. Stack trace following as debug message...")
        logger.debug("".join(traceback.format_stack()))
        return

    logger.exception("Something raised an unhandled exception, it will be sent to the developers")

    def send_to(env, rcv, text, parse_mode, extra_text=None) -> None:
        try:
            msg = env.bot.send_message(rcv, text, parse_mode=parse_mode)
            if extra_text is not None:
                msg.reply_text(extra_text, parse_mode=parse_mode, quote=True)
        except telegram.TelegramError:
            logger.exception(f"Error while sending logs to {rcv}!")

    for receiver in config.config["chats"]["notification"]:
        send_to(
            context,
            receiver,
            f"Unhandled exception: {sys.exc_info()[1]}",
            None
        )

    for receiver in config.config["chats"]["stacktrace"]:
        send_to(
            context,
            receiver,
            f"```\n{traceback.format_exc()}```",
            "MarkdownV2"
        )

    for receiver in config.config["chats"]["debugging"]:
        extra = "No Update object found."
        if update is not None:
            extra = json.dumps(update.to_dict(), indent=2, sort_keys=True)
        send_to(
            context,
            receiver,
            f"```\n{traceback.format_exc()}```",
            "MarkdownV2",
            f"Extended debug information:\n```\n{extra}```"
        )
