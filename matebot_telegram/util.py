import sys
import enum
import json
import asyncio
import logging
import traceback
from typing import Any, Callable, Optional, Union

import requests
import telegram.ext
from matebot_sdk import schemas

from . import config


class PermissionLevel(enum.Enum):
    ANYONE = 0
    ANY_ACTIVE = 1
    ANY_WITH_VOUCHER = 2
    ANY_INTERNAL = 3
    ANY_WITH_PERMISSION = 4
    NOBODY = 5


class FakeTelegramUser:
    def __init__(self, telegram_id: int, name: Optional[str] = None):
        self.id = telegram_id
        self.name = name or "<unknown>"


def get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError(f"Event loop {loop} is closed!")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


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


def extract_alias_from(user: schemas.User) -> Optional[schemas.Alias]:
    aliases = [a for a in user.aliases if a.application == config.config["app"]]
    if len(aliases) == 0:
        return
    return aliases[0]


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
