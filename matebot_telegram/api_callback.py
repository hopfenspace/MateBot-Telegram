"""
MateBot API callback handler implementation
"""

import logging
import collections
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

import telegram
import tornado.web
from matebot_sdk.base import CallbackUpdate


logger = logging.getLogger("api-callback")

CALLBACK_TYPE = Callable[[CallbackUpdate, str, int, telegram.Bot, logging.Logger, ...], Optional[Awaitable[None]]]
STORAGE_TYPE = Dict[
    Tuple[CallbackUpdate, Optional[str]],
    List[Tuple[CALLBACK_TYPE, tuple, dict]]
]


class APICallbackDispatcher:
    def __init__(self):
        self._storage: STORAGE_TYPE = collections.defaultdict(list)

    def register(self, event: Tuple[CallbackUpdate, Optional[str]], func: CALLBACK_TYPE, *args, **kwargs):
        self._storage[event].append((func, args, kwargs))

    async def dispatch(self, method: CallbackUpdate, model: str, model_id: int, bot: telegram.Bot):
        for event in self._storage:
            if event[0] == method and (event[1] is None or event[1] == model):
                for handler in self._storage.get(event):
                    func, args, kwargs = handler
                    try:
                        result = func(method, model, model_id, bot, logger, *args, **kwargs)
                        if result is not None:
                            await result
                    except Exception as exc:
                        logger.warning(f"{type(exc).__name__} in API callback handler for event {event}")
                        raise


dispatcher = APICallbackDispatcher()


class APICallbackApp(tornado.web.Application):
    def __init__(self, bot: telegram.Bot):
        handlers = [(r"(?i)/(create|update|delete)/(.+)/([0-9]+)", APICallbackHandler, {"bot": bot})]
        tornado.web.Application.__init__(self, handlers)

    def log_request(self, handler: tornado.web.RequestHandler) -> None:
        logger.debug(f"Processed callback query request '{handler.request.path}': code {handler.get_status()}")


class APICallbackHandler(tornado.web.RequestHandler):
    bot: telegram.Bot

    def initialize(self, bot: telegram.Bot) -> None:
        self.bot = bot

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise NotImplementedError

    async def get(self, action: str, model: str, model_id: str):
        action = str(action).lower()
        model = str(model).lower()
        model_id = int(model_id)
        logger.debug(f"Incoming callback query: '{action.upper()} {model} {model_id}'")
        method = {
            "create": CallbackUpdate.CREATE,
            "update": CallbackUpdate.UPDATE,
            "delete": CallbackUpdate.DELETE
        }[action]
        await dispatcher.dispatch(method, model, model_id, self.bot)
