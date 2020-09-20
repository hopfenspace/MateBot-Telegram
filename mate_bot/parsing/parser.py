import typing

import telegram

from mate_bot.err import ParsingError
from mate_bot.parsing.util import EntityString, Namespace, Representable
from mate_bot.parsing.usage import CommandUsage
from mate_bot.parsing.actions import Action


class CommandParser(Representable):

    def __init__(self):
        # Add initial default usage
        self._usages = [CommandUsage()]

    @property
    def usages(self) -> typing.List[CommandUsage]:
        """
        Return list of usage objects
        """

        return self._usages

    @property
    def default_usage(self) -> CommandUsage:
        """
        Return the default usage added in constructor
        """

        return self._usages[0]

    def add_argument(self, *args, **kwargs) -> Action:
        """
        Add an argument to the default usage

        See `CommandUsage.add_argument` for type signature
        """

        return self._usages[0].add_argument(*args, **kwargs)

    def new_usage(self) -> CommandUsage:
        """
        Initialize, add and return a new usage object
        """

        self._usages.append(CommandUsage())
        return self._usages[-1]

    def parse(self, msg: telegram.Message) -> Namespace:
        """
        Parse a telegram message into a namespace.

        This just combines the _split and _parse function.

        :param msg: message to parse
        :type msg: telegram.Message
        :return: parsed arguments
        :rtype: Namespace
        """

        arg_strings = list(self._split(msg))
        return self._parse(arg_strings)

    def _parse(self, arg_strings: typing.List[str]) -> Namespace:
        """
        Internal function for parsing from a list of strings.

        :param arg_strings: a list of strings to parse
        :type arg_strings: List[str]
        :return: parsed arguments
        :rtype: Namespace
        """

        # Filter out usages by the minimum and maximum amount of required arguments
        def matching_size(u: CommandUsage) -> bool:
            return u.min_arguments <= len(arg_strings) <= u.max_arguments
        properly_sized = list(filter(matching_size, self._usages))

        # Some usages should have passed this filter
        if len(properly_sized) == 0:
            raise ParsingError("Not enough arguments for any usage")

        # Try the remaining ones
        for usage in properly_sized:
            try:
                return self._apply_usage(usage, arg_strings)
            except RuntimeError:
                continue
        else:
            raise ParsingError("No usage applies")

    @staticmethod
    def _parse_usage(usage: CommandUsage, arg_strings: typing.List[str]) -> Namespace:
        """
        Try to parse the arguments with a usage

        :param usage: the usage to parse the arguments with
        :type usage: CommandUsage
        :param arg_strings: argument strings to parse
        :type arg_strings: List[str]
        :return: parsed arguments
        :rtype: Namespace
        """

        # Initialize namespace and populate it with the defaults
        namespace = Namespace()
        for action in usage.actions:
            setattr(namespace, action.dest, action.default)

        # TODO

        return namespace

    @staticmethod
    def _split(msg: telegram.Message) -> typing.Iterator[EntityString]:
        """
        Split a telegram message into EntityStrings

        This functions splits by spaces while keeping entities intact.

        Danger!!!
        Nested entities would probably break this.

        :param msg: telegram message to tokenize
        :type msg: telegram.Message
        :return: list of argument strings
        :rtype: Iterator[EntityString]
        """

        last_entity = 0

        for entity in msg.entities:
            # If there is normal text left before the next entity
            if last_entity < entity.offset:
                yield from map(EntityString, filter(bool, reversed(msg.text[last_entity:entity.offset].split())))

            yield EntityString(msg.text[entity.offset:entity.offset + entity.length], entity)
            last_entity = entity.offset + entity.length

        # Return left over text which might be after the last entity
        if msg.text[last_entity:]:
            yield from map(EntityString, filter(bool, reversed(msg.text[last_entity:].split())))
