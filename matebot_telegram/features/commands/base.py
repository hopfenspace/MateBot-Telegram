"""
Base class for commands used by this bot

The base class provides argument parsing and error handling for subclasses
"""

import os

import logging
from typing import ClassVar, Dict, Optional

import telegram.ext

from .. import _common
from ... import err
from ...parsing.parser import CommandParser
from ...parsing.util import Namespace


class BaseCommand(_common.CommonBase):
    """
    Base class for all MateBot commands executed by the CommandHandler

    It handles argument parsing and exception catching. Some specific
    implementation should be a subclass of this class. It must add
    arguments to the parser in the constructor and overwrite the run method.

    A minimal working example class may look like this:

    .. code-block::

        class ExampleCommand(BaseCommand):
            def __init__(self):
                super().__init__("example", "Example command")
                self.parser.add_argument("number", type=int)

            async def run(self, args: argparse.Namespace, update: telegram.Update, context: ExtendedContext) -> None:
                await update.effective_message.reply_text(
                    " ".join(["Example!"] * max(1, args.number))
                )

    :param name: name of the command (without the "/")
    :type name: str
    :param description: a multiline string describing what the command does
    :type description: str
    :param usage: a single line string showing the basic syntax
    :type usage: Optional[str]
    """

    ENABLE_HELP: ClassVar[bool] = True
    AVAILABLE_COMMANDS: ClassVar[Dict[str, "BaseCommand"]] = {}

    def __init__(self, name: str, description: str, usage: Optional[str] = None):
        super().__init__(logging.getLogger("mbt.command"))
        self.name = name
        self._usage = usage
        self.description = description
        self.parser = CommandParser(self.name)

        if type(self).ENABLE_HELP:
            BaseCommand.AVAILABLE_COMMANDS[self.name] = self

    @property
    def bot_command(self) -> telegram.BotCommand:
        """
        Get the BotCommand representation of this class (contains no functionality!)
        """

        short_description = self.description.split("\n\n")[0]
        return telegram.BotCommand(self.name, short_description)

    @property
    def usage(self) -> str:
        """
        Get the usage string of a command
        """

        if self._usage is None:
            return f"/{self.name} {self.parser.default_usage}"
        else:
            return self._usage

    async def run(self, args: Namespace, update: telegram.Update, context: _common.ExtendedContext):
        """
        Perform command-specific actions

        This method should be overwritten in actual commands to perform the desired action.

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: _common.ExtendedContext
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseCommand.run() method in a subclass")

    async def __call__(self, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        Parse arguments of the incoming update and execute the .run() method in a separate thread

        This method is the callback method used by telegram.CommandHandler.
        Note that this method also catches and handles ParsingErrors.

        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        """

        try:
            self.logger.debug(f"{type(self).__name__} by {update.effective_message.from_user.name}")
            args = await self.parser.parse(update.effective_message)
            self.logger.debug(f"Parsed {self.name}'s arguments: {args}")
            # TODO: patch user from DB

        except err.MateBotException as exc:
            msg = str(exc)
            self.logger.debug(f"Command failed: {msg.replace(os.linesep, '. ')}")
            try:
                await update.effective_message.reply_markdown(msg)
            except telegram.error.BadRequest:
                await update.effective_message.reply_text(msg)

        else:
            return await self._run(self.run, update.effective_message.reply_text, args, update, context)
