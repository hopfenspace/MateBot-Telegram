"""
MateBot API callback handler implementation
"""

import logging
from typing import Awaitable, Optional

import telegram
import tornado.web


logger = logging.getLogger("api-callback")


class APICallbackApp(tornado.web.Application):
    def __init__(self, bot: telegram.Bot, config: dict):
        handlers = [(r"(?i)/(create|update|delete)/(.+)/([0-9]+)", APICallbackHandler, {"bot": bot, "config": config})]
        tornado.web.Application.__init__(self, handlers)

    def log_request(self, handler: tornado.web.RequestHandler) -> None:
        logger.debug(f"Processed callback query request '{handler.request.path}': code {handler.get_status()}")


class APICallbackHandler(tornado.web.RequestHandler):
    bot: telegram.Bot
    config: dict

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise NotImplementedError

    def initialize(self, bot: telegram.Bot, config: dict) -> None:
        self.bot = bot
        self.config = config

    async def get(self, action: str, model: str, model_id: str):
        action = action.lower()
        model = model.lower()
        model_id = int(model_id)
        logger.debug(f"Incoming callback query: '{action.upper()} {model} {model_id}'")

        # TODO: add actual dispatching of the incoming queries to the specific handlers
