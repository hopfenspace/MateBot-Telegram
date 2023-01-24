"""
MateBot collection of command executors, callback handlers and API callbacks

The configuration entrypoint of this package is the ``setup`` function.

This package is split into subpackages based on type, not
based on functionality. Therefore, functionality for e.g.
communisms can be found in four different subpackages.
"""

import logging

import telegram.ext

try:
    from ..context import ExtendedContext
    from ..application import get_running_app, ExtendedApplication
except ImportError as exc:
    raise ImportError("You need to import this package at runtime in the application's post-initialization") from exc
_app: ExtendedApplication = get_running_app()
if _app is None:
    raise RuntimeError("Do not import this package if the application hasn't been configured yet")


async def setup(logger: logging.Logger, application: ExtendedApplication):
    """
    Setup all handlers for various commands, callbacks, inline queries or messages

    This function performs all in-place operations on the given application object
    to make all functionality of the Telegram bot available at runtime. It will
    also import the required modules inside this function, so that the command
    modules can be sure that certain other modules are ready to be imported, too.
    Therefore, it's required that this function is executed after the
    initialization of the Telegram bot and MateBot SDK, respectively.
    """

    client = _app.client

    # TODO
