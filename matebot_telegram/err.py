"""
MateBot telegram exception classes
"""


class MateBotException(Exception):
    """
    Base class for all project-wide exceptions
    """


class ParsingError(MateBotException):
    """
    Exception raised when the argument parser throws an error

    This is likely to happen when a user messes up the syntax of a
    particular command. Instead of exiting the program, this exception
    will be raised. You may use it's string representation to gain
    additional information about what went wrong. This allows a user
    to correct its command, in case this caused the parser to fail.
    """


class UniqueUserNotFound(MateBotException):
    """
    Exception raised when a user is not found by a unique alias
    """


class NoUserFound(MateBotException):
    """
    Exception raised when no user is found for a given spec, like a username or mention
    """


class AmbiguousUserSpec(MateBotException):
    """
    Exception raised when a user spec, like a username or mention, is ambiguous
    """
