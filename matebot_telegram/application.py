import logging
from typing import Optional

import telegram.ext
import tornado.web

from . import api_callback, client as _client, config as _config


class ExtendedApplication(telegram.ext.Application):
    client: _client.AsyncMateBotSDKForTelegram
    config: _config.Configuration
    logger: logging.Logger
    dispatcher: api_callback.APICallbackDispatcher
    callback_server: tornado.web.HTTPServer

    def __init__(self, config: _config.Configuration, logger: logging.Logger, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.logger = logger

        self.client = None  # noqa, the client has to be set in the post_init method
        self.dispatcher = None  # noqa, the dispatcher has to be set in the post_init method
        self.callback_server = None  # noqa, the callback server has to be set in the post_init method

        global _running_app
        if _running_app is not None:
            self.logger.warning(
                "Multiple applications have been registered. This is NOT supported and may lead "
                "to any type of errors, including race conditions, undefined behavior and crashes."
            )
        else:
            _running_app = self


# Global variables are discouraged but currently required to allow
# access of subsystems like the parser and the commands, which
# dynamically use attributes of the application (usually not
# the application's methods that interact with Telegram). However,
# those subsystems must always use the getter function below
_running_app: Optional[ExtendedApplication] = None


def get_running_app() -> Optional[ExtendedApplication]:
    """
    Return the currently running ExtendedApplication, if any
    """

    return _running_app
