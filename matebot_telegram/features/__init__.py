"""
MateBot collection of command executors, callback handlers and API callbacks

The configuration entrypoint of this package is the ``setup`` function.

This package is split into submodules and subpackages based on functionality
and then grouped based on type. Therefore, functionality for e.g. communisms
can be found in the `communism` subpackage, which has four submodules itself.
"""

import sys as _sys
import json as _json
import time as _time
import asyncio as _asyncio
import logging as _logging
import traceback as _traceback
from typing import Optional as _Optional

import telegram.ext

try:
    from ..context import ExtendedContext as _ExtendedContext
    from ..application import ExtendedApplication as _ExtendedApplication, get_running_app as _get_running_app
except ImportError as _exc:
    raise ImportError("You need to import this package at runtime in the application's post-initialization") from _exc
_app: _ExtendedApplication = _get_running_app()
if _app is None:
    raise RuntimeError("Do not import this package if the application hasn't been configured yet")


async def _handle_error(update: telegram.Update, context: _ExtendedContext) -> None:
    """
    Handle any errors that occurred and were not otherwise caught, possibly including reporting to subscribers
    """

    logger = context.application.logger.getChild("error")
    if update is None:
        logger.debug("Error handler called without Update object. Check for network/connection errors")
        if not await context.application.client.check_telegram_connectivity(context.application.config):
            logger.warning("Connectivity to the Telegram API seems unstable or broken, retrying in one second")
            await _asyncio.sleep(1.0)
            if not await context.application.client.check_telegram_connectivity(context.application.config):
                logger.error("Telegram API connectivity problems")

    if not any(_sys.exc_info()) and getattr(context, "error", None) is None:
        logger.warning("Error handler called without an exception. Stack trace following as debug message...")
        logger.debug("".join(_traceback.format_stack()))
        return

    cls, exc, tb = _sys.exc_info() \
        or (type(context.error), context.error, getattr(context.error, "__traceback__", None))
    logger.error(
        f"Something raised an unhandled {cls} exception, please open a bug report: {exc!s}",
        exc_info=context.error or True
    )
    if tb is None:
        logger.warning("Traceback information is missing")

    async def send_to(rcv, text, extra_text: _Optional[str] = None) -> None:
        try:
            msg = await context.bot.send_message(rcv, text, parse_mode=telegram.constants.ParseMode.MARKDOWN)
            if extra_text is not None:
                await msg.reply_text(extra_text, parse_mode=telegram.constants.ParseMode.MARKDOWN, quote=True)
        except:
            logger.exception(f"Error while sending logs to {rcv}!")
            try:
                await context.bot.send_message(rcv, "An error has occurred, but it crashed the error handler!")
            except Exception as e:
                logger.critical(f"{type(e).__name__} in the additional fallback error handler!", exc_info=True)
                raise
            logger.info("A shortened error message has been emitted successfully.")
            raise

    coroutines = []
    extra = None
    if update is not None:
        formatted_update = _json.dumps(update.to_dict(), indent=2, sort_keys=True)
        extra = f"Extended debug information which *may contain sensitive details*!\n\n```\n{formatted_update}```"
    tb_infos = "Missing traceback information. See logs."
    if tb:
        tb_infos = f"\nTraceback:\n\n```\n{''.join(_traceback.format_exception(cls, exc, tb)[-8:])}```"

    for debug_receiver in context.application.config.chats.debugging:
        coroutines.append(send_to(
            debug_receiver,
            f"*Unhandled exception occurred!*\nTime: {_time.asctime(_time.localtime())}\n"
            f"View the logs for traceback details and consider reporting this as a bug.\n{tb_infos}",
            extra
        ))
    for notification_receiver in context.application.config.chats.notification:
        if notification_receiver in context.application.config.chats.debugging:
            continue
        coroutines.append(send_to(
            notification_receiver,
            "*Unhandled exception occurred!*\nPlease inspect the logs and traces for this exception: "
            f"`{exc!s}`\nIt happened at {_time.asctime(_time.localtime())} local time."
        ))

    results = await _asyncio.gather(*coroutines, return_exceptions=True)
    if any(results):
        logger.warning("Some of the error handlers did not complete successfully")


async def setup(logger: _logging.Logger, application: _ExtendedApplication):
    """
    Setup all handlers for various commands, callbacks, inline queries or messages

    This function performs all in-place operations on the given application object
    to make all functionality of the Telegram bot available at runtime. It will
    also import the required modules inside this function, so that the command
    modules can be sure that certain other modules are ready to be imported, too.
    Therefore, it's required that this function is executed after the
    initialization of the Telegram bot and MateBot SDK, respectively.
    """

    application.add_error_handler(_handle_error)
    client = application.client

    from . import api_callbacks

    from .base.filter import CommandMessageFilter, ReplyMessageFilter

    from .alias import AliasCommand, AliasCallbackQuery
    from .balance import BalanceCommand
    from .blame import BlameCommand
    from .communism import CommunismCommand, CommunismCallbackQuery
    from .consume import ConsumeCommand, get_consumable_commands
    from .data import DataCommand
    from .delete_my_account import DeleteMyAccountCommand, DeleteMyAccountCallbackQuery
    from .donate import DonateCommand, DonateCallbackQuery
    from .forward import ForwardCallbackQuery, ForwardReplyMessage
    from .help import HelpCommand, HelpInlineQuery
    from .history import HistoryCommand
    from .poll import PollCommand, PollCallbackQuery
    from .refund import PayCommand, RefundCommand, RefundCallbackQuery
    from .send import SendCommand, SendCallbackQuery
    from .start import StartCommand, StartCallbackQuery, StartReplyMessage
    from .username import UsernameCommand
    from .vouch import VouchCommand, VouchCallbackQuery
    from .zwegat import ZwegatCommand

    commands = [
        AliasCommand(),
        BalanceCommand(),
        BlameCommand(),
        CommunismCommand(),
        ConsumeCommand(),
        DataCommand(),
        DeleteMyAccountCommand(),
        DonateCommand(),
        HelpCommand(),
        HistoryCommand(),
        PayCommand(),
        PollCommand(),
        RefundCommand(),
        SendCommand(),
        StartCommand(),
        UsernameCommand(),
        VouchCommand(),
        ZwegatCommand()
    ]
    commands.extend(await get_consumable_commands(client))
    for command in commands:
        application.add_handler(telegram.ext.CommandHandler(command.name, command))
    bot_commands = sorted([cmd.bot_command for cmd in commands], key=lambda b: b.command)
    logger.info(f"Configuring {len(bot_commands)} bot commands ...")
    await application.bot.set_my_commands(bot_commands)
    logger.debug("Done.")

    for callback_query in [
        AliasCallbackQuery(),
        CommunismCallbackQuery(),
        DeleteMyAccountCallbackQuery(),
        DonateCallbackQuery(),
        ForwardCallbackQuery(),
        RefundCallbackQuery(),
        PollCallbackQuery(),
        SendCallbackQuery(),
        StartCallbackQuery(),
        VouchCallbackQuery()
    ]:
        application.add_handler(telegram.ext.CallbackQueryHandler(callback_query, pattern=callback_query.pattern))

    application.add_handler(telegram.ext.MessageHandler(ReplyMessageFilter("forward"), ForwardReplyMessage()))
    application.add_handler(telegram.ext.MessageHandler(ReplyMessageFilter("start"), StartReplyMessage()))

    application.add_handler(telegram.ext.InlineQueryHandler(HelpInlineQuery("")))
