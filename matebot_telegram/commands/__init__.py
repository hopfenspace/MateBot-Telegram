"""
MateBot collection of command executors
"""

from .aliases import AliasCallbackQuery
from .balance import BalanceCommand
from .blame import BlameCommand
from .communism import CommunismCommand, CommunismCallbackQuery
from .consume import ConsumeCommand
from .data import DataCommand
from .forward import ForwardInlineQuery, ForwardInlineResult
from .help import HelpCommand, HelpInlineQuery
from .history import HistoryCommand
from .pay import PayCommand
from .refund import RefundCommand, RefundCallbackQuery
from .send import SendCommand, SendCallbackQuery
from .start import StartCommand, StartCallbackQuery
from .vouch import VouchCommand, VouchCallbackQuery
from .zwegat import ZwegatCommand


def setup():
    # In order to register all executors in the registry, we just
    # have to create an object of their corresponding class. The
    # constructors of the base classes care about adding the
    # specific executor object to the correct registry pool.

    BalanceCommand()
    BlameCommand()
    ConsumeCommand()
    CommunismCommand()
    DataCommand()
    HelpCommand()
    HistoryCommand()
    PayCommand()
    RefundCommand()
    SendCommand()
    StartCommand()
    VouchCommand()
    ZwegatCommand()

    AliasCallbackQuery()
    CommunismCallbackQuery()
    RefundCallbackQuery()
    SendCallbackQuery()
    StartCallbackQuery()
    VouchCallbackQuery()

    ForwardInlineQuery(r"^\d+(\s?\S?)*")
    HelpInlineQuery(r"")

    ForwardInlineResult(r"^forward-\d+-\d+-\d+")
