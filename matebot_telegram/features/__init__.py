"""
MateBot collection of command executors, callback handlers and API callbacks

The configuration entrypoint of this package is the ``setup`` function.

This package is split into subpackages based on type, not
based on functionality. Therefore, functionality for e.g.
communisms can be found in four different subpackages.
"""

import logging

import telegram.ext

try:
    from ..context import ExtendedContext
    from ..application import get_running_app, ExtendedApplication
except ImportError as exc:
    raise ImportError("You need to import this package at runtime in the application's post-initialization") from exc
_app: ExtendedApplication = get_running_app()
if _app is None:
    raise RuntimeError("Do not import this package if the application hasn't been configured yet")


async def setup(logger: logging.Logger, application: ExtendedApplication):
    """
    Setup all handlers for various commands, callbacks, inline queries or messages

    This function performs all in-place operations on the given application object
    to make all functionality of the Telegram bot available at runtime. It will
    also import the required modules inside this function, so that the command
    modules can be sure that certain other modules are ready to be imported, too.
    Therefore, it's required that this function is executed after the
    initialization of the Telegram bot and MateBot SDK, respectively.
    """

    client = _app.client

    from . import api_callbacks

    # from .filter import CommandMessageFilter, ReplyMessageHandlerFilter
    # from .forward import ForwardCallbackQuery, ForwardReplyMessage
    # # from .handler import FilteredChosenInlineResultHandler
    # from .message import CatchallReplyMessage

    from .alias import AliasCommand, AliasCallbackQuery
    from .balance import BalanceCommand
    from .blame import BlameCommand
    from .communism import CommunismCommand, CommunismCallbackQuery
    from .consume import ConsumeCommand, get_consumable_commands
    from .data import DataCommand
    from .debug import DebugCommand
    from .donate import DonateCommand, DonateCallbackQuery
    from .help import HelpCommand, HelpInlineQuery
    from .history import HistoryCommand
    from .poll import PollCommand, PollCallbackQuery
    from .refund import PayCommand, RefundCommand, RefundCallbackQuery
    from .send import SendCommand, SendCallbackQuery
    from .start import StartCommand, StartCallbackQuery
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
        DebugCommand(),
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
        DonateCallbackQuery(),
        # ForwardCallbackQuery(),
        RefundCallbackQuery(),
        PollCallbackQuery(),
        SendCallbackQuery(),
        StartCallbackQuery(),
        VouchCallbackQuery()
    ]:
        application.add_handler(telegram.ext.CallbackQueryHandler(callback_query, pattern=callback_query.pattern))

    for message, filter_obj, group in [
        # (ForwardReplyMessage(), ReplyMessageHandlerFilter(True, "forward"), 2),
        # (ConsumeMessage(), CommandMessageFilter(False), 0),
        # (CatchallReplyMessage(), ReplyMessageHandlerFilter(False, None), 2),
    ]:
        application.add_handler(telegram.ext.MessageHandler(filter_obj, message, block=False), group=group)
