"""
Rate limiter implementations of a simple retry mechanism and a BadRequest (parse mode) fixing approach
"""

import asyncio
import logging
from typing import Any, Callable, ClassVar, Coroutine, Dict, List, Optional, Union

import telegram.ext
from telegram._utils.types import JSONDict
from telegram.ext._utils.types import RLARGS


class RetryLimiter(telegram.ext.BaseRateLimiter):
    """
    Rate limiter which is only supposed to log and retry failed requests to the Telegram API

    The retries are restricted to network errors only (rate limit hits, timeouts, connectivity issues).
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


class ParseModeFixingLimiter(RetryLimiter):
    """
    Extended rate limiter which not only retries failed requests but also tries to fix bad requests

    This class builds on the RetryLimiter for retrying failed requests due to network issues.
    Furthermore, it will drop the 'parse_mode' key from the payload data if the response from
    the Telegram API is a Bad Request with the beginning phrase ``Can't parse entities``.
    The class variables `PARSER_ERROR_PHRASE` and `PARSER_ERROR_RETRY` can be tweaked to
    change the behavior of the retry approach, where the first is a phrase expected at the
    beginning of the BadRequest error message and the second is the delay before retrying.
    """

    PARSER_ERROR_PHRASE: ClassVar[str] = "Can't parse entities"
    PARSER_ERROR_RETRY: ClassVar[float] = 0.1

    async def process_request(
        self,
        callback: Callable[..., Coroutine[Any, Any, Union[bool, JSONDict, List[JSONDict]]]],
        args: Any,
        kwargs: Dict[str, Any],
        endpoint: str,
        data: Dict[str, Any],
        rate_limit_args: Optional[RLARGS],
        retry_without_parse_mode: bool = True
    ) -> Union[bool, JSONDict, List[JSONDict]]:
        try:
            return await super().process_request(
                callback,
                args,
                kwargs,
                endpoint,
                data,
                rate_limit_args
            )
        except telegram.error.BadRequest as exc:
            if not str(exc).startswith(type(self).PARSER_ERROR_PHRASE):
                self._logger.warning("Upcoming BadRequest could not be prevented by dropping the parse mode")
                raise
            self._logger.debug(f"BadRequest with parser error encountered for endpoint {endpoint!r}")
            if not retry_without_parse_mode or "parse_mode" not in data:
                raise
            del data["parse_mode"]
            await asyncio.sleep(type(self).PARSER_ERROR_RETRY)
            self._logger.debug(f"Retrying the call to {callback.__name__!r} without 'parse_mode' in the data...")
            result = await self.process_request(
                callback,
                args,
                kwargs,
                endpoint,
                data,
                rate_limit_args,
                retry_without_parse_mode=False
            )
            self._logger.debug("Successfully sent out the callback without parse_mode set in the data")
            self._logger.debug(f"Keys for the successful update were: {list(data.keys())}")
            return result
