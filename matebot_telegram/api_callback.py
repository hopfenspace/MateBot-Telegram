"""
MateBot API callback handler implementation
"""

import json
import asyncio
import inspect
import logging
from typing import Awaitable, Optional

import telegram
import tornado.web

from matebot_sdk import schemas
from matebot_sdk.base import BaseCallbackDispatcher, CALLBACK_TYPE

from . import config, util


dispatcher: Optional["APICallbackDispatcher"] = None  # will be available at runtime


class APICallbackDispatcher(BaseCallbackDispatcher):
    def __init__(self, bot: telegram.Bot):
        super().__init__(logger=logging.getLogger("api-callback"))
        self.bot = bot

        global dispatcher
        dispatcher = self

        self.register(
            schemas.EventType.SERVER_STARTED,
            lambda *_: self.logger.info("Core API server seems to be started now")
        )

    def run_callback(self, func: CALLBACK_TYPE, event: schemas.Event, *args, **kwargs):
        self.logger.debug(f"Handling callback for {event.event}: {func}")
        result = func(event)
        if result is not None:
            if not inspect.isawaitable(result):
                raise TypeError(f"{func} should return Optional[Awaitable[None]], but got {type(result)}")
            if not util.event_loop:
                raise RuntimeError(f"Event loop is not defined, can't run coroutine {result}")
            asyncio.run_coroutine_threadsafe(result, loop=util.event_loop).result()


class APICallbackApp(tornado.web.Application):
    def __init__(self):
        handlers = [(r"/", APICallbackHandler)]
        tornado.web.Application.__init__(self, handlers)
        self.logger = logging.getLogger("api-server")

    def log_request(self, handler: tornado.web.RequestHandler) -> None:
        self.logger.debug(f"Processed callback query request '{handler.request.path}': code {handler.get_status()}")


class APICallbackHandler(tornado.web.RequestHandler):
    logger: logging.Logger

    def initialize(self) -> None:
        self.logger = logging.getLogger("api-handler")
        self.logger.debug("Initialized API callback handler")

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise NotImplementedError

    async def post(self):
        self.logger.debug(f"Incoming POST query from {self.request.remote_ip}")

        auth_header = self.request.headers.get_list("Authorization")
        if len(auth_header) != 1:
            self.logger.warning("API authorization failure, no accepted header provided")
            return
        auth = auth_header[0]
        if not auth.lower().startswith("bearer "):
            self.logger.warning("API authorization failure, not using the 'Bearer' mechanism")
            return
        request_secret = auth[len("Bearer "):]
        if request_secret != config.config.callback.shared_secret:
            self.logger.warning("API authorization failure, invalid shared secret provided")
            return

        try:
            body = self.request.body
            if not body or len(body) < 2:
                self.logger.error("API server sent no request data, no event was recognized")
                return
            notifications = schemas.EventsNotification(**json.loads(body))
        except ValueError:
            self.logger.error("API server sent invalid JSON data or didn't use the event schema")
            return

        self.logger.debug(
            f"Dispatching {notifications.number} events via global dispatcher: "
            f"{[e.event.value for e in notifications.events]}"
        )
        dispatcher.dispatch(notifications)
