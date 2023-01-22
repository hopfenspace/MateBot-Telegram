import threading
import traceback
import logging.config

from telegram.ext import ApplicationBuilder

from matebot_sdk.exceptions import APIConnectionException

# Note that the submodule 'commands' will imported dynamically in the `init` coroutine below
from . import api_callback, application as _app, client, config, rate_limiter, persistence


async def log_error(*args, **kwargs):
    # TODO: Completely rework. Access to sys.exc_info is possible
    traceback.print_exc()


def get_init(logger: logging.Logger):
    async def init(application: _app.ExtendedApplication):
        logger.info("Setting up the SDK")
        logger.debug(f"Running threads: {threading.enumerate()}")

        try:
            callback = None
            if application.config.callback.enabled:
                callback = (application.config.callback.public_url, application.config.callback.shared_secret)
            sdk = client.AsyncMateBotSDKForTelegram(
                base_url=application.config.server,
                app_name=application.config.application,
                password=application.config.password,
                callback=callback,
                logger=logging.getLogger("mbt.client"),
                verify=application.config.ssl_verify and (application.config.ca_path or True),
                user_agent=application.config.user_agent or None
            )
            await sdk.setup()
            application.client = sdk
            logger.debug("Completed SDK setup")

        except APIConnectionException:
            logger.error(
                f"Connecting to the API server failed. Starting the bot is not possible. "
                f"Please verify the connectivity between the API server and the bot. "
                f"Expecting to reach to API server there: {config.config.server}"
            )
            await application.shutdown()
            return

        logger.debug("Adding error handler...")
        application.add_error_handler(log_error)

        logger.debug("Configuring API callback handler")
        application.dispatcher = api_callback.APICallbackDispatcher(logging.getLogger("mbt.api-dispatcher"))

        if not config.config.callback.enabled:
            logger.info("Callbacks have been disabled in the configuration file")
        else:
            app = api_callback.APICallbackApp()
            logger.info(f"Starting tornado callback server on port {config.config.callback.port}")
            application.callback_server = app.listen(
                address=config.config.callback.address,
                port=config.config.callback.port
            )

        logger.debug("Setting up feature handlers (e.g. commands, queries, messages, callbacks) ...")
        try:
            from . import features
        except:
            logger.exception("Failed to import the submodule 'commands'. Check for syntax and import errors!")
            raise
        try:
            await features.setup(logger, application)
        except:
            logger.exception("Failed to setup the submodule 'commands'!")
            raise

    return init


def get_shutdown(logger: logging.Logger):
    async def shutdown(application: _app.ExtendedApplication):
        logger.debug("Shutting down...")
        if hasattr(application, "callback_server") and application.callback_server is not None:
            logger.debug(f"Closing HTTP connections to API server of {application.callback_server}...")
            application.callback_server.stop()
            logger.debug("Stopped callback server")
        if hasattr(application, "client") and application.client is not None:
            logger.debug("Closing SDK ...")
            await application.client.close()
    return shutdown


def main(conf: config.Configuration) -> int:
    logging.config.dictConfig(config.config.logging)
    logger = logging.getLogger("mbt.root")
    logger.info("Starting application ...")

    persistence.init(conf.database_url, echo=conf.database_debug)
    application = ApplicationBuilder() \
        .application_class(_app.ExtendedApplication, {"config": conf, "logger": logging.getLogger("mbt.app")}) \
        .token(config.config.token) \
        .persistence(persistence.BotPersistence()) \
        .post_init(get_init(logging.getLogger("mbt.init"))) \
        .post_shutdown(get_shutdown(logging.getLogger("mbt.shutdown"))) \
        .rate_limiter(rate_limiter.RetryLimiter(logging.getLogger("mbt.limit"))) \
        .build()

    application.run_polling()
    logger.info("Stopped MateBot Telegram.")
    return 0
