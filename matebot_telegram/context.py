"""
Custom extended context type to annotate the return value of some properties correctly
"""

import telegram.ext

from .application import ExtendedApplication as _ExtendedApplication


class ExtendedContext(telegram.ext.CallbackContext[telegram.ext.ExtBot, dict, dict, None]):
    """
    Custom context type to fix type annotations for the extended application
    """

    _application: _ExtendedApplication

    @property
    def application(self) -> _ExtendedApplication:
        return self._application


ExtendedContextType = telegram.ext.ContextTypes(context=ExtendedContext, bot_data=None, chat_data=None, user_data=dict)
