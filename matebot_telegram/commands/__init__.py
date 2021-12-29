"""
MateBot collection of command executors
"""

from matebot_telegram.config import config
from matebot_telegram.commands.balance import BalanceCommand
from matebot_telegram.commands.blame import BlameCommand
from matebot_telegram.commands.communism import CommunismCommand, CommunismCallbackQuery
from matebot_telegram.commands.data import DataCommand
from matebot_telegram.commands.forward import ForwardInlineQuery, ForwardInlineResult
from matebot_telegram.commands.help import HelpCommand, HelpInlineQuery
from matebot_telegram.commands.history import HistoryCommand
from matebot_telegram.commands.pay import PayCommand, PayCallbackQuery
from matebot_telegram.commands.send import SendCommand, SendCallbackQuery
from matebot_telegram.commands.start import StartCommand, StartCallbackQuery
from matebot_telegram.commands.vouch import VouchCommand, VouchCallbackQuery
from matebot_telegram.commands.zwegat import ZwegatCommand
from matebot_telegram.commands.consume import ConsumeCommand


# In order to register all executors in the registry, we just
# have to create an object of their corresponding class. The
# constructors of the base classes care about adding the
# specific executor object to the correct registry pool.

BalanceCommand()
BlameCommand()
CommunismCommand()
DataCommand()
HelpCommand()
HistoryCommand()
PayCommand()
SendCommand()
StartCommand()
VouchCommand()
ZwegatCommand()

for consumable in config["consumables"]:
    ConsumeCommand(**consumable)

CommunismCallbackQuery()
PayCallbackQuery()
SendCallbackQuery()
StartCallbackQuery()
VouchCallbackQuery()

ForwardInlineQuery(r"^\d+(\s?\S?)*")
HelpInlineQuery(r"")

ForwardInlineResult(r"^forward-\d+-\d+-\d+")
