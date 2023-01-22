"""
MateBot API callback handler implementation
"""

import json
import inspect
import logging
from typing import Awaitable, Optional

import tornado.web

from matebot_sdk import schemas
from matebot_sdk.base import BaseCallbackDispatcher, CALLBACK_TYPE

# Note that there's another import in the functions at the bottom of the file
from . import config


class APICallbackDispatcher(BaseCallbackDispatcher):
    """
    Dispatcher class that handles the registered callback coroutines for certain events

    To register a new callback coroutine, use the `register` or `register_for` methods.
    """

    def __init__(self, logger: logging.Logger):
        super().__init__(logger=logger)

        self.register(
            schemas.EventType.SERVER_STARTED,
            lambda *_: self.logger.info("Core API server seems to be started now")
        )

    async def dispatch(self, events: schemas.EventsNotification):
        """
        Dispatch an incoming event notification to trigger all registered callback handlers
        """

        for event in events.events:
            for target, args, kwargs in self._storage.get(event.event, []):
                try:
                    await self.run_callback(target, event, target, *args, **kwargs)
                except Exception as exc:
                    self.logger and self.logger.exception(
                        f"{type(exc).__name__} in callback handler {target} for event {event!r} with {args}, {kwargs}"
                    )

    async def run_callback(self, func: CALLBACK_TYPE, event: schemas.Event, *args, **kwargs):
        """
        Process a single event by calling the callback function with its specified args and kwargs
        """

        self.logger.debug(f"Handling callback for {event.event}: {func}")
        result = func(event)
        if result is not None:
            if not inspect.isawaitable(result):
                raise TypeError(f"{func} should return Optional[Awaitable[None]], but got {type(result)}")
            return await result


class APICallbackApp(tornado.web.Application):
    """
    Simple tornado web app that just recognizes '/' to accept callback events from the API server
    """

    def __init__(self):
        handlers = [(r"/", APICallbackHandler)]
        tornado.web.Application.__init__(self, handlers)
        self.logger = logging.getLogger("mbt.api-app")

    def log_request(self, handler: tornado.web.RequestHandler) -> None:
        self.logger.debug(f"Processed callback query request '{handler.request.path}': code {handler.get_status()}")


class APICallbackHandler(tornado.web.RequestHandler):
    """
    Handler class that checks auth, unpacks the payload and forwards the events to the dispatcher
    """

    logger: logging.Logger

    def initialize(self) -> None:
        self.logger = logging.getLogger("mbt.api-handler")
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
        if request_secret != _get_config().callback.shared_secret:
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
            f"Dispatching {notifications.number} event(s): "
            f"{[e.event.value for e in notifications.events]}"
        )
        dispatcher = _get_dispatcher()
        if dispatcher is None:
            self.logger.error(f"No dispatcher registered. {notifications.number} incoming events are ignored!")
        else:
            try:
                await _get_dispatcher().dispatch(notifications)
            except:
                self.logger.exception("Unhandled exception while handling callback events")
                raise


# Avoiding cyclic imports by moving access to the Application into two functions
def _get_config() -> Optional[config.Configuration]:
    from . import application
    app = application.get_running_app()
    if app is not None:
        return app.config


def _get_dispatcher() -> Optional[APICallbackDispatcher]:
    from . import application
    app = application.get_running_app()
    if app is not None:
        return app.dispatcher
