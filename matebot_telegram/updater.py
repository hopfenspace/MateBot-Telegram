"""
MateBot's patched version of the telegram Updater
"""

import asyncio
import threading

import telegram.ext
import tornado.ioloop

from . import util
from .api_callback import APICallbackApp
from .client import SDK


SERVER_THREAD_JOIN_TIMEOUT = 0.2


class PatchedUpdater(telegram.ext.Updater):
    """
    Patched version of the updater to closely integrate the API callback server
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_server = None
        self.callback_server_thread = None

    def start_api_callback_server(self, config: dict):
        app = APICallbackApp(self.bot)
        self.callback_server = app.listen(address=config["address"], port=config["port"])
        self.callback_server_thread = threading.Thread(
            target=tornado.ioloop.IOLoop.current().start,
            daemon=True,
            name=f"Bot:{self.bot.id}:callback-api",)
        self.callback_server_thread.start()

    def stop(self) -> None:
        self.logger.debug("Executing 'stop'...")
        asyncio.run_coroutine_threadsafe(SDK.close(), loop=util.event_loop).result()
        self.callback_server.stop()
        self.logger.debug("Stopped callback server")
        result = super().stop()
        util.event_thread_running.set()
        if self.callback_server_thread:
            self.callback_server_thread.join(timeout=SERVER_THREAD_JOIN_TIMEOUT)
        self.logger.debug(f"Callback server thread alive state: {self.callback_server_thread.is_alive()}")
        return result
