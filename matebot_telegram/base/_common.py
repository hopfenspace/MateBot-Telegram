"""
Common base class to provide a wrapper for base classes for operations of the Telegram MateBot
"""

import logging
from typing import Awaitable, Callable, TypeVar

from matebot_sdk.exceptions import APIException, APIConnectionException

from .. import err
from ..context import ExtendedContext
from ..application import get_running_app

_ = ExtendedContext  # re-exporting the `ExtendedContext` class
FUNC_ARG_TYPE = TypeVar("FUNC_ARG_TYPE")
FUNC_ARG_RETURN_TYPE = TypeVar("FUNC_ARG_RETURN_TYPE")


class CommonBase:
    """
    Common base class providing a run wrapper that catches and handles various exceptions
    """

    logger: logging.Logger

    def __init__(self, logger_suffix: str):
        self.logger: logging.Logger = get_running_app().logger.getChild(logger_suffix).getChild(type(self).__name__)

    async def _run(
            self,
            func: Callable[[FUNC_ARG_TYPE], Awaitable[FUNC_ARG_RETURN_TYPE]],
            reply: Callable[[str], Awaitable[None]],
            *args: FUNC_ARG_TYPE
    ) -> FUNC_ARG_RETURN_TYPE:
        """
        Execute the given coroutine with the specified arguments, using the reply coroutine for error reporting
        """

        try:
            return await func(*args)

        except APIConnectionException as exc:
            self.logger.exception(f"API connectivity problem @ {type(self).__name__} ({exc.exc})")
            await reply("There are temporary networking problems. Please try again later.")

        except APIException as exc:
            self.logger.warning(
                f"APIException @ {type(self).__name__} ({exc.status}, {exc.details}): {exc.message!r}",
                exc_info=exc.status != 400
            )
            await reply(exc.message)

        except err.MateBotException as exc:
            msg = str(exc)
            self.logger.debug(f"Uncaught MateBotException will now be replied to user: {msg!r}")
            await reply(msg)
