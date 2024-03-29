"""
MateBot command handling base library
"""

import logging
from typing import Awaitable, Callable, ClassVar, Dict, Optional, Tuple

import telegram.ext

from matebot_sdk.exceptions import APIException, APIConnectionException

from . import client, config, err, util
from .parsing.parser import CommandParser
from .parsing.util import Namespace


class _CommonBase:
    client: client.AsyncMateBotSDKForTelegram
    config: config.Configuration

    def __init__(self):
        self.client: client.AsyncMateBotSDKForTelegram = client.client
        self.config: config.Configuration = config.config


class BaseCommand(_CommonBase):
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

            def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
                update.effective_message.reply_text(
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
        super().__init__()
        self.name = name
        self._usage = usage
        self.description = description
        self.parser = CommandParser(self.name)
        self.logger = logging.getLogger("command")

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

    def run(self, args: Namespace, update: telegram.Update) -> Optional[Awaitable[None]]:
        """
        Perform command-specific actions

        This method should be overwritten in actual commands to perform the desired action.

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseCommand.run() method in a subclass")

    def _run(self, values: Tuple[Namespace, telegram.Update, telegram.ext.CallbackContext]):
        args, update, context = values
        try:
            util.execute_func(self.run, self.logger, args, update)

        except APIConnectionException as exc:
            self.logger.exception(f"API connectivity problem @ {type(self).__name__} ({exc.exc})")
            update.effective_message.reply_text("There are temporary networking problems. Please try again later.")

        except APIException as exc:
            self.logger.warning(f"APIException @ {type(self).__name__} ({exc.status}, {exc.details})", exc_info=True)
            update.effective_message.reply_text(exc.message)

        except err.MateBotException as exc:
            msg = str(exc)
            self.logger.debug("Uncaught MateBotException will now be replied to user")
            util.safe_call(
                lambda: update.effective_message.reply_markdown(msg),
                lambda: update.effective_message.reply_text(msg),
                logger=self.logger
            )

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
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

            args = self.parser.parse(update.effective_message)
            self.logger.debug(f"Parsed {self.name}'s arguments: {args}")
            self.client.patch_user_db_from_update(update)

        except err.MateBotException as exc:
            msg = str(exc)
            util.safe_call(
                lambda: update.effective_message.reply_markdown(msg),
                lambda: update.effective_message.reply_text(msg),
                logger=self.logger
            )

        else:
            self._run((args, update, context))


class BaseCallbackQuery(_CommonBase):
    """
    Base class for all MateBot callback queries executed by the CallbackQueryHandler

    It provides the stripped data of a callback button as string in the
    data attribute. Some specific implementation should be a subclass of
    this class. It must provide the constructor's parameter `targets` to
    work properly. The `targets` parameter is a dictionary connecting the
    data with associated function calls. Those functions or methods must
    expect one parameter `update` which is filled with the correct
    ``telegram.Update`` object. Any return value is ignored.

    In order to properly use this class or a subclass thereof, you
    must supply a pattern to filter the callback query against to
    the CallbackQueryHandler. This pattern must start with `^` to
    ensure that it's the start of the callback query data string.
    Furthermore, this pattern must match the name you give as
    first argument to the constructor of this class.

    Example: Imagine you have a command `/hello`. The callback query
    data should by convention start with "hello". So, you set
    "hello" as the name of this handler. Furthermore, you set
    "^hello" as pattern to filter callback queries against.

    :param name: name of the command the callback is for
    :type name: str
    :param pattern: regular expression to filter callback query executors
    :type pattern: str
    :param targets: dict to associate data replies with function calls
    :type targets: Dict[str, Callable[[telegram.Update], Any]]
    """

    name: str
    pattern: str
    targets: Dict[str, Callable[[telegram.Update], Optional[Awaitable[None]]]]
    data: Optional[str]
    logger: logging.Logger

    def __init__(
            self,
            name: str,
            pattern: str,
            targets: Dict[str, Callable[[telegram.Update], Optional[Awaitable[None]]]]
    ):
        super().__init__()
        if not isinstance(targets, dict):
            raise TypeError("Expected dict or None")

        self.name = name
        self.pattern = pattern
        self.data = None
        self.targets = targets
        self.logger = logging.getLogger("callback")
        self.client: client.AsyncMateBotSDKForTelegram = client.client
        self.config = config.config

    def _run(self, args: Tuple[Callable[[telegram.Update], Optional[Awaitable[None]]], telegram.Update]):
        target, update = args
        try:
            util.execute_func(target, self.logger, update)

        except APIException as exc:
            self.logger.info(f"{type(exc).__name__}: {exc.message} ({exc.status}, {exc.details})")
            update.callback_query.answer(text=exc.message, show_alert=True)

        except APIConnectionException as exc:
            self.logger.exception(f"{type(exc).__name__}: {exc.message} ({exc.exc}: {exc.exc.args}, {exc.details})")
            update.callback_query.answer(
                text="There are temporary networking problems. Please try again later.",
                show_alert=True
            )
            raise

        except Exception as exc:
            self.logger.warning(f"{type(exc).__name__}: {exc!s}")
            update.callback_query.answer(
                text="There was an error processing your request. You may file a bug report.",
                show_alert=True
            )
            raise

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises RuntimeError: when either no callback data or no pattern match is present
        :raises IndexError: when a callback data string has no unique target callable
        :raises TypeError: when a target is not a callable object (implicitly)
        """

        data = update.callback_query.data
        self.logger.debug(f"{type(self).__name__} by {update.callback_query.from_user.name} with '{data}'")

        if data is None:
            raise RuntimeError("No callback data found")
        if context.match is None:
            raise RuntimeError("No pattern match found")

        try:
            self.client.patch_user_db_from_update(update)
            self.data = (data[:context.match.start()] + data[context.match.end():]).strip()

            if self.data in self.targets:
                target = self.targets[self.data]

            else:
                available = []
                for k in self.targets:
                    if self.data.startswith(k):
                        available.append(k)

                if len(available) == 0:
                    raise IndexError(f"No target callable found for: '{self.data}' ({type(self).__name__})")
                if len(available) > 1:
                    raise IndexError(f"No unambiguous callable found for: '{self.data}' ({type(self).__name__})")
                target = self.targets[available[0]]

        except (IndexError, ValueError, TypeError, RuntimeError):
            update.callback_query.answer(
                text="There was an error processing your request. You may file a bug report.",
                show_alert=True
            )
            raise

        self._run((target, update))


class BaseInlineQuery(_CommonBase):
    """
    Base class for all MateBot inline queries executed by the InlineQueryHandler

    :param pattern: regular expression to filter inline query executors
    :type pattern: str
    """

    def __init__(self, pattern: str):
        super().__init__()
        self.pattern = pattern
        self.logger = logging.getLogger("inline")
        self.client: client.AsyncMateBotSDKForTelegram = client.client
        self.config = config.config

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises TypeError: when no inline query is attached to the Update object
        """

        if not hasattr(update, "inline_query"):
            raise TypeError('Update object has no attribute "inline_query"')

        query = update.inline_query
        self.logger.debug(f"{type(self).__name__} by {query.from_user.name} with '{query.query}'")
        self.client.patch_user_db_from_update(update)
        self.run(query)

    def get_result_id(self, *args) -> str:
        """
        Get the ID of the inline result based on the given arguments

        :param args: any form of arguments that might be useful to create the result ID
        :type args: typing.Any
        :return: unique ID of the returned inline result so that the ChosenInlineResult
            can be parsed and used accurately (note that it doesn't need to be really unique)
        :rtype: str
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.get_result_id() method in a subclass")

    def get_result(
            self,
            heading: str,
            msg_text: str,
            *args,
            parse_mode: str = None,
            result_id: str = None
    ) -> telegram.InlineQueryResultArticle:
        """
        Get an article as possible inline result for an inline query

        :param heading: bold text (head line) the user clicks/taps on to select the inline result
        :type heading: str
        :param msg_text: text that will be sent from the client via the bot
        :type msg_text: str
        :param args: arguments passed to :meth:`get_result_id`
        :type args: typing.Any
        :param parse_mode: parse mode that should be used to parse this text (default: Markdown v1)
        :type parse_mode: typing.Optional[str]
        :param result_id: specify the result ID of the inline result instead of generating it
        :type result_id: typing.Optional[str]
        :return: inline query result (of type article)
        :rtype: telegram.InlineQueryResultArticle
        """

        return telegram.InlineQueryResultArticle(
            id=result_id or self.get_result_id(*args),
            title=heading,
            input_message_content=telegram.InputTextMessageContent(
                message_text=msg_text,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
        )

    def get_help(self) -> telegram.InlineQueryResult:
        """
        Get some kind of help message as inline result (always as first item!)

        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.get_help() method in a subclass")

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Perform feature-specific operations

        :param query: inline query as part of an incoming Update
        :type query: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.run() method in a subclass")


class BaseInlineResult(_CommonBase):
    """
    Base class for all MateBot inline query results executed by the ChosenInlineResultHandler

    :param pattern: regular expression to filter inline result executors
    :type pattern: str
    """

    def __init__(self, pattern: str):
        super().__init__()
        self.pattern = pattern
        self.logger = logging.getLogger("inline-result")
        self.client: client.AsyncMateBotSDKForTelegram = client.client
        self.config = config.config

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises TypeError: when no inline result is attached to the Update object
        """

        if not hasattr(update, "chosen_inline_result"):
            raise TypeError('Update object has no attribute "chosen_inline_result"')

        result = update.chosen_inline_result
        self.logger.debug(f"{type(self).__name__} by {result.from_user.name} with '{result.result_id}'")
        self.client.patch_user_db_from_update(update)
        self.run(result, context.bot)

    def run(self, result: telegram.ChosenInlineResult, bot: telegram.Bot) -> None:
        """
        Perform feature-specific operations

        :param result: report of the chosen inline query option as part of an incoming Update
        :type result: telegram.ChosenInlineResult
        :param bot: currently used Telegram Bot object
        :type bot: telegram.Bot
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.run() method in a subclass")


class BaseMessage(_CommonBase):
    """
    Base class for all MateBot message handlers

    :param prefix: unique name of the associated command or feature
    :type prefix: str
    """

    def __init__(self, prefix: Optional[str]):
        super().__init__()
        self.prefix = prefix
        self.logger = logging.getLogger("message")
        self.client: client.AsyncMateBotSDKForTelegram = client.client
        self.config = config.config

    def run(self, message: telegram.Message, context: telegram.ext.CallbackContext) -> Optional[Awaitable[None]]:
        """
        Perform handler-specific actions

        This method should be overwritten in actual handlers to perform the desired action.

        :param message: incoming effective Telegram message which was filtered to contain a reply to a bot message
        :type message: telegram.Message
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: Optional[Awaitable[None]]
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseMessage.run() method in a subclass")

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises TypeError: when no inline result is attached to the Update object
        """

        msg = update.effective_message
        self.logger.debug(f"{type(self).__name__} by {msg.from_user.name}: '{msg.text}'")
        util.execute_func(self.run, self.logger, msg, context)
