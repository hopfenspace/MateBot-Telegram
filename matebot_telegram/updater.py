"""
MateBot's patched version of the telegram Updater
"""

import threading

import telegram.ext
import tornado.ioloop

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

    def start_api_callback_server(self, config: dict):
        app = APICallbackApp()
        self.callback_server = app.listen(address=config["address"], port=config["port"])
        self.callback_server_thread = threading.Thread(
            target=tornado.ioloop.IOLoop.current().start,
            daemon=True,
            name=f"Bot:{self.bot.id}:callback-api",)
        self.callback_server_thread.start()

    def stop(self) -> None:
        self.callback_server.stop()
        # TODO: gracefully shutdown the SDK client
        # util.get_event_loop().run_until_complete(SDK.close())
        result = super().stop()
        if self.callback_server_thread:
            self.callback_server_thread.join(timeout=SERVER_THREAD_JOIN_TIMEOUT)
        return result
