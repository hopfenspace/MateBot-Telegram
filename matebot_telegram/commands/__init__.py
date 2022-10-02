"""
MateBot collection of command executors

The configuration entrypoint of this package is the ``setup`` function.
"""

from telegram.ext import (
    Dispatcher as _Dispatcher,
    CommandHandler as _CommandHandler,
    CallbackQueryHandler as _CallbackQueryHandler,
    InlineQueryHandler as _InlineQueryHandler,
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

    from .aliases import AliasCallbackQuery
    from .balance import BalanceCommand
    from .blame import BlameCommand
    from .communism import CommunismCommand, CommunismCallbackQuery
    from .consume import ConsumeCommand
    from .data import DataCommand
    from .filter import ReplyMessageHandlerFilter
    from .forward import ForwardInlineQuery, ForwardInlineResult
    from .handler import FilteredChosenInlineResultHandler
    from .help import HelpCommand, HelpInlineQuery
    from .history import HistoryCommand
    from .pay import PayCommand
    from .refund import RefundCommand, RefundCallbackQuery
    from .send import SendCommand, SendCallbackQuery
    from .start import StartCommand, StartCallbackQuery, StartMessage
    from .vouch import VouchCommand, VouchCallbackQuery
    from .zwegat import ZwegatCommand

    for command in [
        BalanceCommand(),
        BlameCommand(),
        ConsumeCommand(),
        CommunismCommand(),
        DataCommand(),
        HelpCommand(),
        HistoryCommand(),
        PayCommand(),
        RefundCommand(),
        SendCommand(),
        StartCommand(),
        VouchCommand(),
        ZwegatCommand()
    ]:
        dispatcher.add_handler(_CommandHandler(command.name, command, run_async=True), group=0)

    for callback_query in [
        AliasCallbackQuery(),
        CommunismCallbackQuery(),
        RefundCallbackQuery(),
        SendCallbackQuery(),
        StartCallbackQuery(),
        VouchCallbackQuery()
    ]:
        dispatcher.add_handler(_CallbackQueryHandler(callback_query, pattern=callback_query.pattern, run_async=True))

    for inline_query in [
        ForwardInlineQuery(r"^\d+(\s?\S?)*"),
        HelpInlineQuery(r"")
    ]:
        dispatcher.add_handler(_InlineQueryHandler(inline_query, pattern=inline_query.pattern, run_async=True))

    for inline_result in [
        ForwardInlineResult(r"^forward-\d+-\d+-\d+")
    ]:
        dispatcher.add_handler(
            FilteredChosenInlineResultHandler(inline_result, pattern=inline_result.pattern, run_async=True)
        )

    for message, group in [
        (StartMessage(), 1)
    ]:
        dispatcher.add_handler(
            _MessageHandler(ReplyMessageHandlerFilter(False, message.prefix), message, run_async=True),
            group=group
        )
