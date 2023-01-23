"""
Base class for callback queries used by this bot

The base class provides target method detection and error handling for subclasses
"""

import logging
from typing import Awaitable, Callable, Dict, Optional

import telegram.ext

from .. import _common


class BaseCallbackQuery(_common.CommonBase):
    """
    Base class for all MateBot callback queries executed by the CallbackQueryHandler

    It provides the stripped data of a callback button as string in the
    data attribute. Some specific implementation should be a subclass of
    this class. It must provide the constructor's parameter `targets` to
    work properly. The `targets` parameter is a dictionary connecting the
    data with associated function calls. Those functions or methods must
    expect one parameter `update` which is filled with the correct
    ``telegram.Update`` object. Any return value is ignored.

    In order to properly use this class or a subclass thereof, you
    must supply a pattern to filter the callback query against to
    the CallbackQueryHandler. This pattern must start with `^` to
    ensure that it's the start of the callback query data string.
    Furthermore, this pattern must match the name you give as
    first argument to the constructor of this class.

    Example: Imagine you have a command `/hello`. The callback query
    data should by convention start with "hello". So, you set
    "hello" as the name of this handler. Furthermore, you set
    "^hello" as pattern to filter callback queries against.

    :param name: name of the command the callback is for
    :type name: str
    :param pattern: regular expression to filter callback query executors
    :type pattern: str
    :param targets: dict to associate data replies with function calls
    :type targets: Dict[str, Callable[[telegram.Update, _common.ExtendedContext], Optional[Awaitable[None]]]]
    """

    name: str
    pattern: str
    targets: Dict[str, Callable[[telegram.Update, _common.ExtendedContext], Optional[Awaitable[None]]]]
    logger: logging.Logger

    def __init__(
            self,
            name: str,
            pattern: str,
            targets: Dict[str, Callable[[telegram.Update, _common.ExtendedContext], Optional[Awaitable[None]]]]
    ):
        super().__init__(logging.getLogger("mbt.callback"))
        if not isinstance(targets, dict):
            raise TypeError("Expected dict or None")

        self.name = name
        self.pattern = pattern
        self.targets = targets

    async def __call__(self, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: extended Telegram callback context
        :type context: ExtendedContext
        :return: None
        :raises RuntimeError: when either no callback data or no pattern match is present
        :raises IndexError: when a callback data string has no unique target callable
        :raises TypeError: when a target is not a callable object (implicitly)
        """

        data = update.callback_query.data
        self.logger.debug(f"{type(self).__name__} by {update.callback_query.from_user.name} with '{data}'")

        if data is None:
            raise RuntimeError("No callback data found")
        if context.match is None:
            raise RuntimeError("No pattern match found")

        try:
            # self.client.patch_user_db_from_update(update)  # TODO
            self.data = (data[:context.match.start()] + data[context.match.end():]).strip()

            if self.data in self.targets:
                target = self.targets[self.data]

            else:
                available = []
                for k in self.targets:
                    if self.data.startswith(k):
                        available.append(k)

                if len(available) == 0:
                    raise IndexError(f"No target callable found for: '{self.data}' ({type(self).__name__})")
                if len(available) > 1:
                    raise IndexError(f"No unambiguous callable found for: '{self.data}' ({type(self).__name__})")
                target = self.targets[available[0]]

        except (IndexError, ValueError, TypeError, RuntimeError):
            await update.callback_query.answer(
                text="There was an error processing your request. You may file a bug report.",
                show_alert=True
            )
            raise

        await self._run(target, update.callback_query.answer, update, context)
