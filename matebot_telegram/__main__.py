#!/usr/bin/env python3

import argparse
import logging.config

from matebot_sdk.exceptions import APIConnectionException

from matebot_telegram import api_callback, client, commands, config, updater as _updater, util


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="path to the configuration file")
    return parser


def main():
    args = get_parser().parse_args()
    if args.config:
        config.setup_configuration(args.config)

    logging.config.dictConfig(config.config.logging)
    logger = logging.getLogger("root")

    logger.info("Registering bot token with Updater...")
    updater = _updater.PatchedUpdater(config.config.token, workers=config.config.workers)

    logger.debug("Starting event thread...")
    util.event_thread.start()
    logger.debug("Started event thread.")
    util.event_thread_started.wait()
    logger.debug(f"Started event {util.event_thread_started}: {util.event_thread_started.is_set()}")

    try:
        api_callback.APICallbackDispatcher(updater.bot)
        client.client = client.setup(updater.bot, config.config)
    except APIConnectionException as exc:
        logger.critical(
            f"Connecting to the API server failed! Please review your "
            f"config and ensure {config.config.server} is reachable: {exc!s}"
        )
        updater.callback_server and updater.callback_server.stop()
        util.event_thread_running.set()
        raise

    logger.debug("Setting up feature handlers (e.g. commands, queries, messages, callbacks) ...")
    commands.setup(updater.dispatcher)

    logger.debug("Adding error handler...")
    updater.dispatcher.add_error_handler(util.log_error)

    logger.info("Starting API callback server...")
    updater.start_api_callback_server()

    logger.info("Starting bot...")
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
