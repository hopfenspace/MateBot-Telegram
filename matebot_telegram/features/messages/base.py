

import logging
from typing import Awaitable, Callable, Dict, Optional, Tuple, TypeVar

import telegram.ext

from matebot_sdk.exceptions import APIException, APIConnectionException

from .. import _app, _common
from ... import client, config, err


class BaseMessage(_common.CommonBase):
    """
    Base class for all MateBot message handlers

    :param prefix: unique name of the associated command or feature
    :type prefix: str
    """

    def __init__(self, prefix: Optional[str]):
        super().__init__(logging.getLogger("mbt.message"))
        self.prefix = prefix
        self.client: client.AsyncMateBotSDKForTelegram = client.client
        self.config = config.config

    def run(self, message: telegram.Message, context: telegram.ext.CallbackContext) -> Optional[Awaitable[None]]:
        """
        Perform handler-specific actions

        This method should be overwritten in actual handlers to perform the desired action.

        :param message: incoming effective Telegram message which was filtered to contain a reply to a bot message
        :type message: telegram.Message
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: Optional[Awaitable[None]]
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseMessage.run() method in a subclass")

    async def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises TypeError: when no inline result is attached to the Update object
        """

        msg = update.effective_message
        self.logger.debug(f"{type(self).__name__} by {msg.from_user.name}: '{msg.text}'")
        # util.execute_func(self.run, self.logger, msg, context) # TODO
