"""
MateBot API callback handler implementation
"""

import asyncio
import inspect
import logging
from typing import Awaitable, Callable, Optional

import telegram
import tornado.web
from matebot_sdk.base import BaseCallbackDispatcher, CallbackUpdate

from . import util


CALLBACK_TYPE = Callable[[CallbackUpdate, str, int, telegram.Bot, logging.Logger, ...], Optional[Awaitable[None]]]


class APICallbackDispatcher(BaseCallbackDispatcher):
    def __init__(self, bot: telegram.Bot):
        super().__init__(logger=logging.getLogger("api-callback"))
        self.bot = bot

    def run_callback(self, func: CALLBACK_TYPE, method: CallbackUpdate, model: str, model_id: int, *args, **kwargs):
        result = func(method, model, model_id, self.bot, self.logger, *args, **kwargs)
        if result is not None:
            if not inspect.isawaitable(result):
                raise TypeError(f"{func} should return Optional[Awaitable[None]], but got {type(result)}")
            if not util.event_loop:
                raise RuntimeError(f"Event loop is not defined, can't run coroutine {result}")
            asyncio.run_coroutine_threadsafe(result, loop=util.event_loop).result()


class APICallbackApp(tornado.web.Application):
    def __init__(self, bot: telegram.Bot):
        handlers = [(r"(?i)/(create|update|delete)/(.+)/([0-9]+)", APICallbackHandler, {"bot": bot})]
        tornado.web.Application.__init__(self, handlers)
        self.logger = logging.getLogger("api-server")

    def log_request(self, handler: tornado.web.RequestHandler) -> None:
        self.logger.debug(f"Processed callback query request '{handler.request.path}': code {handler.get_status()}")


class APICallbackHandler(tornado.web.RequestHandler):
    logger: logging.Logger
    dispatcher: APICallbackDispatcher

    def initialize(self, bot: telegram.Bot) -> None:
        self.logger = logging.getLogger("api-handler")
        self.dispatcher = APICallbackDispatcher(bot)

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise NotImplementedError

    async def get(self, action: str, model: str, model_id: str):
        action = str(action).lower()
        model = str(model).lower()
        model_id = int(model_id)
        self.logger.debug(f"Incoming callback query: '{action.upper()} {model} {model_id}'")
        method = {
            "create": CallbackUpdate.CREATE,
            "update": CallbackUpdate.UPDATE,
            "delete": CallbackUpdate.DELETE
        }[action]
        self.dispatcher.dispatch(method, model, model_id)
