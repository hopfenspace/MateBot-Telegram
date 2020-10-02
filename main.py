#!/usr/bin/env python3

import logging

from telegram.ext import (
    Updater, CommandHandler,
    CallbackQueryHandler,
    Filters, InlineQueryHandler
)


from mate_bot import err
from mate_bot import log
from mate_bot.config import config
from mate_bot.commands.handler import FilteredChosenInlineResultHandler
from mate_bot.commands.registry import COMMANDS as COMMAND_REGISTRY
from mate_bot.commands.communism import (
    CommunismCallbackQuery,
    CommunismInlineQuery,
    CommunismInlineResult
)
from mate_bot.commands.help import HelpInlineQuery
from mate_bot.commands.send import SendCallbackQuery
from mate_bot.commands.vouch import VouchCallbackQuery


COMMANDS = {
    Filters.all: COMMAND_REGISTRY.commands_as_dict
}

HANDLERS = {
    CallbackQueryHandler: {
        "^communism": CommunismCallbackQuery(),
        # "^pay": PayQuery(),
        "^send": SendCallbackQuery(),
        "^vouch": VouchCallbackQuery()
    },
    InlineQueryHandler: {
        r"^\d+(\s?\S?)*": CommunismInlineQuery(),
        "": HelpInlineQuery()
    },
    FilteredChosenInlineResultHandler: {
        "": CommunismInlineResult()
    }
}


if __name__ == "__main__":
    log.setup()
    logger = logging.getLogger()

    updater = Updater(config["bot"]["token"], use_context = True)
    internal_filter = Filters.chat(config["bot"]["chat"])

    logger.info("Adding error handler...")
    updater.dispatcher.add_error_handler(err.log_error)

    logger.info("Adding command handlers...")
    for cmd_filter, commands in COMMANDS.items():
        for name, cmd in commands.items():
            updater.dispatcher.add_handler(
                CommandHandler(name, cmd, filters=cmd_filter)
            )

    logger.info("Adding other handlers...")
    for handler in HANDLERS:
        for pattern in HANDLERS[handler]:
            updater.dispatcher.add_handler(handler(HANDLERS[handler][pattern], pattern=pattern))

    logger.info("Starting bot...")
    updater.start_polling()
    updater.idle()
