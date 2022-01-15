import sys
import json
import asyncio
import logging
import traceback
from typing import Any, Callable, List, Optional

import requests
import telegram.ext

from .config import config
from .shared_messages import shared_message_handler


def get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError(f"Event loop {loop} is closed!")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def safe_call(
        default: Callable[[], Any],
        fallback: Callable[[], Any],
        use_result: bool = False,
        logger: logging.Logger = None
) -> Any:
    try:
        result = default()
        return result if use_result else True
    except telegram.error.BadRequest as exc:
        if not str(exc).startswith("Can't parse entities"):
            raise
        logger = logger or logging.getLogger(__name__)
        logger.exception(f"Calling sender function {default} failed due to entity parsing problems: {exc!s}")
        result = fallback()
        logger.debug(f"Calling fallback function {fallback} was successful instead.")
        return result if use_result else False


def send_auto_share_messages(
        bot: telegram.Bot,
        share_type: str,
        share_id: int,
        text: str,
        logger: Optional[logging.Logger] = None,
        keyboard: Optional[telegram.InlineKeyboardMarkup] = None,
        excluded: List[int] = None,
        try_parse_mode: telegram.ParseMode = telegram.ParseMode.MARKDOWN,
        disable_notification: bool = True
) -> bool:
    logger = logger or logging.getLogger(__name__)
    excluded = excluded or []
    if share_type not in config["auto-forward"]:
        return False
    receivers = [*map(int, config["auto-forward"][share_type])]
    logger.debug(f"Configured receivers of {share_type} ({share_id}) auto-forward: {receivers}")
    for receiver in receivers:
        if receiver in excluded:
            continue
        message = safe_call(
            lambda: bot.send_message(
                chat_id=receiver,
                text=text,
                parse_mode=try_parse_mode,
                disable_notification=disable_notification,
                reply_markup=keyboard,
            ),
            lambda: bot.send_message(
                chat_id=receiver,
                text=text,
                disable_notification=disable_notification,
                reply_markup=keyboard,
            ),
            use_result=True
        )
        shared_message_handler.add_message_by(share_type, share_id, message.chat_id, message.message_id)
        logger.debug(f"Added message {message.message_id} in chat {message.chat_id} to {share_type} ({share_id})")
    return True


def update_all_shared_messages(
        bot: telegram.Bot,
        share_type: str,
        share_id: int,
        text: str,
        logger: Optional[logging.Logger] = None,
        keyboard: Optional[telegram.InlineKeyboardMarkup] = None,
        try_parse_mode: telegram.ParseMode = telegram.ParseMode.MARKDOWN
) -> bool:
    logger = logger or logging.getLogger(__name__)
    shared_messages = shared_message_handler.get_messages_of(share_type, share_id)
    logger.debug(f"Found shared messages for {share_type} ({share_id}): {[s.to_dict() for s in shared_messages]}")
    success = True
    for msg in shared_messages:
        success = success and safe_call(
            lambda: bot.edit_message_text(
                text=text,
                chat_id=msg.chat_id,
                message_id=msg.message_id,
                parse_mode=try_parse_mode,
                reply_markup=keyboard
            ),
            lambda: bot.edit_message_text(
                text=text,
                chat_id=msg.chat_id,
                message_id=msg.message_id,
                reply_markup=keyboard
            )
        )
        logger.debug(f"Updated message {msg.message_id} in chat {msg.chat_id} by {share_type} ({share_id})")
    return success


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
        token = config["token"]
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
            try:
                env.bot.send_message(rcv, "An error has occurred, but it crashed the error handler.")
            except Exception as exc:
                logger.critical(f"{type(exc).__name__} in the additional fallback error handler!", exc_info=True)
                raise
            logger.info("A shortened error message has been emitted successfully.")

    for receiver in config["chats"]["notification"]:
        send_to(
            context,
            receiver,
            f"Unhandled exception: {sys.exc_info()[1]}",
            None
        )

    for receiver in config["chats"]["stacktrace"]:
        send_to(
            context,
            receiver,
            f"```\n{traceback.format_exc()}```",
            "MarkdownV2"
        )

    for receiver in config["chats"]["debugging"]:
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
