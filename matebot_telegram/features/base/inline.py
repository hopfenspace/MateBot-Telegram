"""
Base class for inline queries and inline results used by this bot

The base class provides argument parsing and error handling for subclasses
"""

import logging

import telegram.ext

from ._common import CommonBase, ExtendedContext


class BaseInlineQuery(CommonBase):
    """
    Base class for all MateBot inline queries executed by the InlineQueryHandler

    :param pattern: regular expression to filter inline query executors
    :type pattern: str
    """

    def __init__(self, pattern: str):
        super().__init__(logging.getLogger("mbt.inline"))
        self.pattern = pattern

    async def __call__(self, update: telegram.Update, context: ExtendedContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: extended Telegram callback context
        :type context: ExtendedContext
        :return: None
        :raises TypeError: when no inline query is attached to the Update object
        """

        if not hasattr(update, "inline_query"):
            raise TypeError('Update object has no attribute "inline_query"')

        query = update.inline_query
        self.logger.debug(f"{type(self).__name__} by {query.from_user.name} with '{query.query}'")
        # self.client.patch_user_db_from_update(update)  # TODO
        await self.run(query)

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

    async def run(self, query: telegram.InlineQuery) -> None:
        """
        Perform feature-specific operations

        :param query: inline query as part of an incoming Update
        :type query: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.run() method in a subclass")


class BaseInlineResult(CommonBase):
    """
    Base class for all MateBot inline query results executed by the ChosenInlineResultHandler

    :param pattern: regular expression to filter inline result executors
    :type pattern: str
    """

    def __init__(self, pattern: str):
        super().__init__(logging.getLogger("mbt.inline-result"))
        self.pattern = pattern

    async def __call__(self, update: telegram.Update, context: ExtendedContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: extended Telegram callback context
        :type context: ExtendedContext
        :return: None
        :raises TypeError: when no inline result is attached to the Update object
        """

        if not hasattr(update, "chosen_inline_result"):
            raise TypeError('Update object has no attribute "chosen_inline_result"')

        result = update.chosen_inline_result
        self.logger.debug(f"{type(self).__name__} by {result.from_user.name} with '{result.result_id}'")
        # self.client.patch_user_db_from_update(update)  # TODO
        await self.run(result, context.bot)

    async def run(self, result: telegram.ChosenInlineResult, bot: telegram.Bot) -> None:
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
