"""
Rate limiter implementations of a simple retry mechanism and a BadRequest (parse mode) fixing approach
"""

import asyncio
import logging
import dataclasses
from typing import Any, Callable, ClassVar, Coroutine, Dict, List, Optional, Union

import telegram.ext
from telegram._utils.types import JSONDict


@dataclasses.dataclass
class RLArgs:
    """
    Dataclass as argument storage for the rate limiter implementations

    Note that not all rate limiter implementations may use all of the fields defined here.
    """

    base_retry_delay: Optional[float] = None
    fix_parser_errors: Optional[bool] = None
    max_retries: Optional[int] = None


class RetryLimiter(telegram.ext.BaseRateLimiter):
    """
    Rate limiter which is only supposed to log and retry failed requests to the Telegram API

    The retries are restricted to network errors only (rate limit hits,
    timeouts, connectivity issues). There's a configurable maximum for the
    number of retries made. The class provides a default value in the class
    variable `MAX_RETRIES` but it could be overridden by the `rate_limit_args`
    argument (see the class ``RLArgs``). Note that if the value is unset (which
    is also the default), there's no maximum number of retries, so the method
    `process_request` will basically never complete unless succeeded! If you
    encounter network issues, this could lead to problems of de-synchronization
    and messages being sent out-of-order or delayed. For timeouts, the base
    delay will be used and doubled for every further error in the retry chain.
    """

    MAX_RETRIES: ClassVar[Optional[int]] = None
    BASE_RETRY_DELAY: ClassVar[float] = 0.1

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
        rate_limit_args: Optional[RLArgs]
    ) -> Union[bool, JSONDict, List[JSONDict]]:
        """
        Process a callback request but also handle rate limits and timeout errors
        """

        current_retries = 0
        max_retries = (rate_limit_args and rate_limit_args.max_retries) or type(self).MAX_RETRIES
        timeout_retry = (rate_limit_args and rate_limit_args.base_retry_delay) or type(self).BASE_RETRY_DELAY
        while True:
            try:
                return await callback(*args, **kwargs)
            except telegram.error.RetryAfter as exc:
                # Not waiting the full delayed time is sometimes useful to speed up execution for high delays
                t = round(float(exc.retry_after) / 2, 1) if exc.retry_after > 5 else float(exc.retry_after)
                self._logger.info(f"Rate limit hit. Retrying call to {endpoint!r} in {t} of {exc.retry_after} seconds.")
                await asyncio.sleep(t / 2)
            except telegram.error.TimedOut:
                self._logger.info(f"Timeout occurred. Retrying call to {endpoint!r} in {timeout_retry} seconds.")
                await asyncio.sleep(timeout_retry)
                timeout_retry *= 2
            except telegram.error.TelegramError as exc:
                self._logger.warning(f"Unhandled exception from communication with Telegram: {exc!r}")
                raise
            finally:
                current_retries += 1
                if max_retries and 0 <= max_retries < current_retries:
                    raise


class ParseModeFixingLimiter(RetryLimiter):
    """
    Extended rate limiter which not only retries failed requests but also tries to fix bad requests

    This class builds on the RetryLimiter for retrying failed requests due to
    network issues. Furthermore, it will drop the 'parse_mode' key from the
    payload data if the response from the Telegram API is a Bad Request with
    the beginning phrase ``Can't parse entities``. The class variable
    `PARSER_ERROR_PHRASE` can be tweaked to change the retry approach, since
    it's the phrase expected at the beginning of the BadRequest error message.
    """

    PARSER_ERROR_PHRASE: ClassVar[str] = "Can't parse entities"

    async def process_request(
        self,
        callback: Callable[..., Coroutine[Any, Any, Union[bool, JSONDict, List[JSONDict]]]],
        args: Any,
        kwargs: Dict[str, Any],
        endpoint: str,
        data: Dict[str, Any],
        rate_limit_args: Optional[RLArgs]
    ) -> Union[bool, JSONDict, List[JSONDict]]:
        """
        Process a callback request but also handle parser errors, rate limits and timeout errors
        """

        rate_limit_args = rate_limit_args or RLArgs(fix_parser_errors=True)

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
                self._logger.debug("Upcoming BadRequest could not be prevented by dropping the parse mode")
                raise
            self._logger.debug(f"BadRequest with parser error encountered for endpoint {endpoint!r}")
            if not rate_limit_args.fix_parser_errors or "parse_mode" not in data:
                raise
            del data["parse_mode"]
            await asyncio.sleep(type(self).BASE_RETRY_DELAY)

            rate_limit_args.fix_parser_errors = False
            self._logger.debug(f"Retrying the call to {callback.__name__!r} without 'parse_mode' in the data...")
            result = await self.process_request(
                callback,
                args,
                kwargs,
                endpoint,
                data,
                rate_limit_args
            )
            self._logger.debug("Successfully sent out the callback without parse_mode set in the data")
            self._logger.debug(f"Keys for the successful update were: {list(data.keys())}")
            return result
