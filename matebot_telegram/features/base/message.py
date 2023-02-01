"""
Base class for Telegram message handling used by this bot

The base class provides argument parsing and error handling for subclasses
"""

from typing import Optional

import telegram.ext

from ._common import CommonBase, ExtendedContext
from .. import _app


class BaseMessage(CommonBase):
    """
    Base class for all MateBot message handlers

    :param prefix: unique name of the associated command or feature
    :type prefix: str
    """

    def __init__(self, prefix: Optional[str]):
        super().__init__(_app.logger.getChild("message").getChild(type(self).__name__))
        self.prefix = prefix

    async def run(self, message: telegram.Message, context: ExtendedContext) -> None:
        """
        Perform handler-specific actions

        This method should be overwritten in actual handlers to perform the desired action.

        :param message: incoming effective Telegram message which was filtered to contain a reply to a bot message
        :type message: telegram.Message
        :param context: extended Telegram callback context
        :type context: ExtendedContext
        :return: Optional[Awaitable[None]]
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseMessage.run() method in a subclass")

    async def __call__(self, update: telegram.Update, context: ExtendedContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: extended Telegram callback context
        :type context: ExtendedContext
        :return: None
        :raises TypeError: when no inline result is attached to the Update object
        """

        msg = update.effective_message
        self.logger.debug(f"{type(self).__name__} by {msg.from_user.name}: '{msg.text}'")
        # util.execute_func(self.run, self.logger, msg, context) # TODO
        await self._run(self.run, msg.reply_text, update.effective_message, context)
