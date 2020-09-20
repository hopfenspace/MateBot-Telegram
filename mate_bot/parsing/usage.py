from mate_bot.parsing.util import Representable
from mate_bot.parsing.actions import Action, StoreAction


class CommandUsage(Representable):
    """
    A CommandUsage represents a command's use case.

    A command can have multiple use cases with conflicting arguments.
    These objects hold the arguments for one such use case and the parser
    tries which usage applies to a given set of arguments.
    """

    def __init__(self):
        self._actions = []

    @property
    def actions(self):
        return self._actions

    def add_argument(self, dest: str, **kwargs) -> Action:
        if "action" in kwargs:
            action_type = kwargs["action"]
            del kwargs["action"]
        else:
            action_type = StoreAction

        self._actions.append(action_type(dest, **kwargs))

        return self._actions[0]

    @property
    def min_arguments(self) -> int:
        """
        Return the minimum required amount of arguments.
        """
        return sum(map(lambda x: x.min_args, self.actions))

    @property
    def max_arguments(self) -> int:
        """
        Return the maximum allowed amount of arguments
        """
        return sum(map(lambda x: x.max_args, self.actions))
