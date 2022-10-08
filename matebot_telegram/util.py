"""
MateBot telegram utility library
"""

import sys
import json
import asyncio
import inspect
import logging
import threading
import traceback
from typing import Any, Awaitable, Callable, List, Optional

import requests
import telegram.ext

from matebot_sdk import exceptions

from . import client, config, shared_messages


ASYNC_SLEEP_DURATION: float = 0.5

event_loop: Optional[asyncio.AbstractEventLoop] = None
event_thread_running: threading.Event = threading.Event()
event_thread_started: threading.Event = threading.Event()

_logger = logging.getLogger("util")


async def async_thread():
    global event_loop
    global event_thread_running
    global event_thread_started

    event_loop = asyncio.get_event_loop()
    _logger.debug(f"Event loop {event_loop} of {threading.current_thread()} has been announced globally")
    event_thread_started.set()

    _logger.debug(f"Sleeping until {event_thread_running} gets set...")
    while not event_thread_running.is_set():
        await asyncio.sleep(ASYNC_SLEEP_DURATION)
    _logger.info(f"Closing async thread {threading.current_thread()}...")


event_thread: threading.Thread = threading.Thread(target=lambda: asyncio.run(async_thread()), name="AsyncWorkerThread")


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
        logger = logger or _logger
        logger.exception(f"Calling sender function {default} failed due to entity parsing problems: {exc!s}")
        result = fallback()
        logger.debug(f"Calling fallback function {fallback} was successful instead.")
        return result if use_result else False


def send_auto_share_messages(
        bot: telegram.Bot,
        share_type: shared_messages.ShareType,
        share_id: int,
        text: str,
        logger: Optional[logging.Logger] = None,
        keyboard: Optional[telegram.InlineKeyboardMarkup] = None,
        excluded: List[int] = None,
        try_parse_mode: telegram.ParseMode = telegram.ParseMode.MARKDOWN,
        disable_notification: bool = True,
        job_queue: Optional[telegram.ext.JobQueue] = None
) -> bool:
    if job_queue is not None:
        def _send_auto_share_messages(_):
            send_auto_share_messages(
                bot,
                share_type,
                share_id,
                text,
                logger,
                keyboard,
                excluded,
                try_parse_mode,
                disable_notification,
                None
            )

        (logger or _logger).debug(f"Detaching auto share message call for {share_type} {share_id} to job queue")
        job_queue.run_once(_send_auto_share_messages, 0)
        return True

    logger = logger or _logger
    excluded = excluded or []
    if not hasattr(config.config.auto_forward, share_type.value):
        logger.warning(f"No auto-forward rules defined for {share_type}!")
        return False
    receivers = getattr(config.config.auto_forward, share_type.value)
    logger.debug(f"Configured receivers of {share_type} ({share_id}) auto-forward: {receivers}")
    for receiver in receivers:
        shared_message = client.client.shared_messages.get_messages(share_type, share_id)
        if receiver in [int(m.chat_id) for m in shared_message] + excluded:
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
        client.client.shared_messages.add_message_by(share_type, share_id, message.chat_id, message.message_id)
        logger.debug(f"Added message {message.message_id} in chat {message.chat_id} to {share_type} ({share_id})")
    return True


def update_all_shared_messages(
        bot: telegram.Bot,
        share_type: shared_messages.ShareType,
        share_id: int,
        text: str,
        logger: Optional[logging.Logger] = None,
        keyboard: Optional[telegram.InlineKeyboardMarkup] = None,
        try_parse_mode: telegram.ParseMode = telegram.ParseMode.MARKDOWN,
        delete_shared_messages: bool = False,
        job_queue: Optional[telegram.ext.JobQueue] = None
) -> bool:
    if job_queue is not None:
        def _update_all_shared_messages(_):
            update_all_shared_messages(
                bot,
                share_type,
                share_id,
                text,
                logger,
                keyboard,
                try_parse_mode,
                delete_shared_messages,
                None
            )

        (logger or _logger).debug(f"Detaching update share message call for {share_type} {share_id} to job queue")
        job_queue.run_once(_update_all_shared_messages, 0)
        return True

    def edit_msg(**kwargs):
        try:
            bot.edit_message_text(text=text, **kwargs)
        except telegram.error.BadRequest as exc:
            if not str(exc).startswith("Message is not modified: specified new message content"):
                raise

    logger = logger or _logger
    msgs = client.client.shared_messages.get_messages(share_type, share_id)
    logger.debug(f"Found {len(msgs)} shared messages for {share_type} ({share_id})")
    success = True
    for msg in msgs:
        success = success and safe_call(
            lambda: edit_msg(
                chat_id=msg.chat_id,
                message_id=msg.message_id,
                parse_mode=try_parse_mode,
                reply_markup=keyboard
            ),
            lambda: edit_msg(
                chat_id=msg.chat_id,
                message_id=msg.message_id,
                reply_markup=keyboard
            )
        )
        logger.debug(f"Updated message {msg.message_id} in chat {msg.chat_id} by {share_type} ({share_id})")
    if success:
        logger.debug("Successfully updated all shared messages")
    else:
        logger.warning(f"Failed to update at least one shared message for {share_type} {share_id}")
    if delete_shared_messages:
        client.client.shared_messages.delete_messages(share_type, share_id)
        logger.debug(f"Dropped the shared message database entry for {share_type} {share_id}")
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
        token = config.config.token
        response = requests.get(f"https://api.telegram.org/bot{token}/getme")
        if response.status_code != 200:
            logger.error("Network check failed. Telegram API seems to be unreachable.")
        else:
            logger.debug("Network check succeeded. Telegram API seems to be reachable.")

    if not any(sys.exc_info()) and getattr(context, "error", None) is None:
        logger.error("Error handler called without an exception. Stack trace following as debug message...")
        logger.debug("".join(traceback.format_stack()))
        return

    cls, exc, tb = sys.exc_info() or (type(context.error), context.error, getattr(context.error, "__traceback__", None))
    logger.exception(
        f"Something raised an unhandled {cls} exception, it will be sent to the developers",
        exc_info=context.error or True
    )
    if tb is None:
        logger.error("Traceback information is missing")

    def send_to(env, rcv, text, parse_mode, extra_text=None) -> None:
        try:
            msg = env.bot.send_message(rcv, text, parse_mode=parse_mode)
            if extra_text is not None:
                msg.reply_text(extra_text, parse_mode=parse_mode, quote=True)
        except telegram.TelegramError:
            logger.exception(f"Error while sending logs to {rcv}!")
            try:
                env.bot.send_message(rcv, "*An error has occurred, but it crashed the error handler!*")
            except Exception as e:
                logger.critical(f"{type(e).__name__} in the additional fallback error handler!", exc_info=True)
                raise
            logger.info("A shortened error message has been emitted successfully.")

    for receiver in config.config.chats.notification:
        send_to(
            context,
            receiver,
            f"Unhandled exception: {exc}",
            None
        )

    for receiver in config.config.chats.stacktrace:
        send_to(
            context,
            receiver,
            f"```\n{traceback.format_exception(cls, exc, tb)}```" if tb else "Missing traceback information. See logs.",
            "Markdown"
        )

    for receiver in config.config.chats.debugging:
        extra = "No Update object found."
        if update is not None:
            extra = json.dumps(update.to_dict(), indent=2, sort_keys=True)
        send_to(
            context,
            receiver,
            f"```\n{traceback.format_exception(cls, exc, tb)}```" if tb else "Missing traceback information. See logs.",
            "Markdown",
            f"Extended debug information:\n```\n{extra}```"
        )


def execute_func(func: Callable[..., Optional[Awaitable]], logger: logging.Logger, *args, **kwargs):
    """
    Execute the given function or coroutine (on the target event loop in the later case) and await it
    """

    result = func(*args, **kwargs)
    if result is not None:
        if not inspect.isawaitable(result):
            raise TypeError(f"'run' should return Optional[Awaitable[None]], but got {type(result)}")

        try:
            return asyncio.run_coroutine_threadsafe(result, loop=event_loop).result()
        except exceptions.APIException as exc:
            logger.warning(f"Unhandled exception from future of {result}: {type(exc).__name__}")
            raise
        except Exception as exc:
            logger.warning(
                f"Unhandled exception from future of {result}: {type(exc).__name__}",
                exc_info=True
            )
            raise
