"""
MateBot's patched version of the telegram Updater
"""

import asyncio
import threading

import telegram.ext
import tornado.ioloop

from . import client, config, util
from .api_callback import APICallbackApp


SERVER_THREAD_JOIN_TIMEOUT = 0.2


class PatchedUpdater(telegram.ext.Updater):
    """
    Patched version of the updater to closely integrate the API callback server
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback_server = None
        self.callback_server_thread = None

    def start_api_callback_server(self):
        if not config.config.callback.enabled:
            self.logger.info("Callbacks have been disabled in the configuration file.")
            return
        app = APICallbackApp(self.bot)
        self.callback_server = app.listen(address=config.config.callback.address, port=config.config.callback.port)
        self.callback_server_thread = threading.Thread(
            target=tornado.ioloop.IOLoop.current().start,
            daemon=True,
            name=f"Bot:{self.bot.id}:callback-api"
        )
        self.callback_server_thread.start()

    def stop(self) -> None:
        self.logger.debug("Executing 'stop'...")
        self.callback_server.stop()
        self.logger.debug("Stopped callback server")
        result = super().stop()
        self.logger.debug(f"Closing HTTP connections to API server of {client.client} ...")
        if client.client is not None:
            asyncio.run_coroutine_threadsafe(client.client.close(), loop=util.event_loop).result()
        util.event_thread_running.set()
        if self.callback_server_thread:
            self.callback_server_thread.join(timeout=SERVER_THREAD_JOIN_TIMEOUT)
        self.logger.debug(f"Callback server thread state: {('alive','dead')[self.callback_server_thread.is_alive()]}")
        return result
