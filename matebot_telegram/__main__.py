#!/usr/bin/env python3

import typing
import logging.config

from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, InlineQueryHandler
from matebot_sdk.exceptions import APIConnectionException

from matebot_telegram import client, config, registry, updater, util
from matebot_telegram.commands.handler import FilteredChosenInlineResultHandler


handler_types = typing.Union[
    typing.Type[CommandHandler],
    typing.Type[CallbackQueryHandler],
    typing.Type[InlineQueryHandler],
    typing.Type[FilteredChosenInlineResultHandler]
]


def _add(dispatcher: Dispatcher, handler: handler_types, pool: dict, pattern: bool = True) -> None:
    """
    Add the executors from the given pool to the dispatcher using the given handler type

    :param dispatcher: Telegram's dispatcher to add the executor to
    :type dispatcher: telegram.ext.Dispatcher
    :param handler: type of the handler (subclass of ``telegram.ext.Handler``)
    :type handler: handler_types
    :param pool: collection of all executors for one handler type
    :type pool: dict
    :param pattern: switch whether the keys of the pool are patterns or names
    :type pattern: bool
    :return: None
    """

    logger.debug(f"Adding {handler.__name__} executors...")
    for name in pool:
        if pattern:
            dispatcher.add_handler(handler(pool[name], pattern=name))
        else:
            dispatcher.add_handler(handler(name, pool[name], run_async=False))


class NoDebugFilter(logging.Filter):
    """
    Logging filter that filters out any DEBUG message for the specified logger or handler
    """

    def filter(self, record: logging.LogRecord) -> int:
        if super().filter(record):
            return record.levelno > logging.DEBUG
        return True


if __name__ == "__main__":
    logging.config.dictConfig(config.config["logging"])
    logger = logging.getLogger("root")

    logger.info("Registering bot token with Updater...")
    updater = updater.PatchedUpdater(config.config["token"], workers=1)

    logger.debug("Adding error handler...")
    updater.dispatcher.add_error_handler(util.log_error)

    _add(updater.dispatcher, CommandHandler, registry.commands, False)
    _add(updater.dispatcher, CallbackQueryHandler, registry.callback_queries, True)
    _add(updater.dispatcher, InlineQueryHandler, registry.inline_queries, True)
    _add(updater.dispatcher, FilteredChosenInlineResultHandler, registry.inline_results, True)

    logger.info("Starting API callback server...")
    updater.start_api_callback_server(config.config["callback"])

    logger.debug("Starting event thread...")
    util.event_thread.start()
    logger.debug("Started event thread.")
    util.event_thread_started.wait()
    logger.debug(f"Started event {util.event_thread_started}: {util.event_thread_started.is_set()}")

    try:
        client.setup_sdk(updater.bot, config.config["database-url"])
    except APIConnectionException as exc:
        logger.critical(
            f"Connecting to the API server failed! Please review your "
            f"config and ensure {config.config['server']} is reachable."
        )
        updater.callback_server.stop()
        util.event_thread_running.set()
        raise

    logger.info("Starting bot...")
    updater.start_polling()
    updater.idle()
