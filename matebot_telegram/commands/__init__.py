"""
MateBot collection of command executors

The configuration entrypoint of this package is the ``setup`` function.
"""

from telegram.ext import (
    Dispatcher as _Dispatcher,
    CommandHandler as _CommandHandler,
    CallbackQueryHandler as _CallbackQueryHandler,
    MessageHandler as _MessageHandler
)


def setup(dispatcher: _Dispatcher):
    """
    Setup all handlers for various commands, callbacks, inline queries or messages

    This function performs all in-place operations on the given dispatcher object
    to make all functionality of the Telegram bot available at runtime. It will
    also import the required modules inside this function, so that the command
    modules can be sure that certain other modules are ready to be imported, too.
    Therefore, it's required that this function is executed after the
    initialization of the Telegram bot and MateBot SDK, respectively.
    """

    from .aliases import AliasCommand, AliasCallbackQuery
    from .balance import BalanceCommand
    from .blame import BlameCommand
    from .communism import CommunismCommand, CommunismCallbackQuery
    from .consume import ConsumeCommand, ConsumeMessage
    from .data import DataCommand
    from .donate import DonateCommand, DonateCallbackQuery
    from .filter import CommandMessageFilter, ReplyMessageHandlerFilter
    from .forward import ForwardCallbackQuery, ForwardReplyMessage
    from .handler import FilteredChosenInlineResultHandler
    from .help import HelpCommand, HelpInlineQuery
    from .history import HistoryCommand
    from .message import CatchallReplyMessage
    from .pay import PayCommand
    from .polls import PollCommand, PollCallbackQuery
    from .refund import RefundCommand, RefundCallbackQuery
    from .send import SendCommand, SendCallbackQuery
    from .start import StartCommand, StartCallbackQuery
    from .username import UsernameCommand
    from .vouch import VouchCommand, VouchCallbackQuery
    from .zwegat import ZwegatCommand

    from .. import config
    if not hasattr(config, "config"):
        raise RuntimeError("Initialize the config module completely before executing this function!")

    from .. import client
    if not hasattr(client, "client"):
        raise RuntimeError("Initialize the client module using its 'setup' function before executing this function!")

    from .. import api_callback
    if api_callback.dispatcher is None:
        raise RuntimeError("Initialize the 'api_callback' module and its 'dispatcher' before executing this function!")

    for command in [
        AliasCommand(),
        BalanceCommand(),
        BlameCommand(),
        ConsumeCommand(),
        CommunismCommand(),
        DataCommand(),
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
    ]:
        dispatcher.add_handler(
            _CommandHandler(command.name, command, run_async=True),
            group=0
        )

    for callback_query in [
        AliasCallbackQuery(),
        CommunismCallbackQuery(),
        DonateCallbackQuery(),
        ForwardCallbackQuery(),
        RefundCallbackQuery(),
        PollCallbackQuery(),
        SendCallbackQuery(),
        StartCallbackQuery(),
        VouchCallbackQuery()
    ]:
        dispatcher.add_handler(
            _CallbackQueryHandler(callback_query, pattern=callback_query.pattern, run_async=True),
            group=1
        )

    for message, filter_obj, group in [
        (ForwardReplyMessage(), ReplyMessageHandlerFilter(True, "forward"), 2),
        (ConsumeMessage(), CommandMessageFilter(False), 0),
        (CatchallReplyMessage(), ReplyMessageHandlerFilter(False, None), 2),
    ]:
        dispatcher.add_handler(_MessageHandler(filter_obj, message, run_async=True), group=group)
