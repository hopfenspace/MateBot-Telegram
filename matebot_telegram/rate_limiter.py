"""
Rate limiter implementations, currently only with a simple retry implementation
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

import telegram.ext
from telegram._utils.types import JSONDict
from telegram.ext._utils.types import RLARGS


class RetryLimiter(telegram.ext.BaseRateLimiter):
    """
    Rate limiter which is only supposed to log and retry failed requests to the Telegram API
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def process_request(
        self,
        callback: Callable[..., Coroutine[Any, Any, Union[bool, JSONDict, List[JSONDict]]]],
        args: Any,
        kwargs: Dict[str, Any],
        endpoint: str,
        data: Dict[str, Any],
        rate_limit_args: Optional[RLARGS]
    ) -> Union[bool, JSONDict, List[JSONDict]]:
        timeout_retry = 0.1
        while True:
            try:
                return await callback(*args, **kwargs)
            except telegram.error.RetryAfter as exc:
                self._logger.info(f"Rate limit hit. Retrying {callback} in {exc.retry_after} seconds.")
                await asyncio.sleep(exc.retry_after)
            except telegram.error.TimedOut:
                self._logger.info(f"Timeout occurred. Retrying {callback} in {timeout_retry} seconds.")
                await asyncio.sleep(timeout_retry)
                timeout_retry *= 2
            except telegram.error.TelegramError as exc:
                self._logger.warning(f"Unhandled exception from communication with Telegram: {exc!r}")
                raise
