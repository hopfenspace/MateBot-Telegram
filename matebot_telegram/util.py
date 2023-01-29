"""
MateBot telegram utility library
"""

import sys
import json
import logging
import threading
import traceback

import telegram.ext

from . import config


_logger = logging.getLogger("mbt.util")
_auto_send_lock = threading.Lock()


async def log_error(update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
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

    async def send_to(env, rcv, text, parse_mode, extra_text=None) -> None:
        try:
            msg = await env.bot.send_message(rcv, text, parse_mode=parse_mode)
            if extra_text is not None:
                msg.reply_text(extra_text, parse_mode=parse_mode, quote=True)
        except telegram.TelegramError:
            logger.exception(f"Error while sending logs to {rcv}!")
            try:
                await env.bot.send_message(rcv, "*An error has occurred, but it crashed the error handler!*")
            except Exception as e:
                logger.critical(f"{type(e).__name__} in the additional fallback error handler!", exc_info=True)
                raise
            logger.info("A shortened error message has been emitted successfully.")

    for receiver in config.config.chats.notification:
        await send_to(
            context,
            receiver,
            f"Unhandled exception: {exc}",
            None
        )

    for receiver in config.config.chats.stacktrace:
        await send_to(
            context,
            receiver,
            f"```\n{traceback.format_exception(cls, exc, tb)}```" if tb else "Missing traceback information. See logs.",
            "Markdown"
        )

    for receiver in config.config.chats.debugging:
        extra = "No Update object found."
        if update is not None:
            extra = json.dumps(update.to_dict(), indent=2, sort_keys=True)
        await send_to(
            context,
            receiver,
            f"```\n{traceback.format_exception(cls, exc, tb)}```" if tb else "Missing traceback information. See logs.",
            "Markdown",
            f"Extended debug information:\n```\n{extra}```"
        )


