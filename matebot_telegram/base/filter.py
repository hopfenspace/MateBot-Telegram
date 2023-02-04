"""
Telegram update filter classes

The classes provided in this module allow filtering of updates to
the handler based on various criteria. Currently, those are bot commands
which are not handled by the command handler (including commands to
other bots in case of group chats) in the class ``CommandMessageFilter``
and messages which are a direct reply to a message sent by the bot itself
in the ``ReplyMessageFilter`` class (with optional inline keyboard).
"""

from typing import Optional

import telegram.ext

from ._common import get_running_app


class CommandMessageFilter(telegram.ext.filters.MessageFilter):
    """
    Update filter for messages which are Telegram bot commands starting with '/'
    """

    def filter(self, msg: telegram.Message) -> bool:
        cmd = telegram.MessageEntity.BOT_COMMAND
        if msg.from_user.is_bot or not msg.entities or msg.entities[0].type != cmd or not msg.text.startswith("/"):
            return False
        return True


class ReplyMessageFilter(telegram.ext.filters.MessageFilter):
    """
    Message filter to only allow messages which are a reply to a message from the bot

    Optionally restricts those messages to must contain a callback inline keyboard,
    where all available buttons have a known common command prefix.
    """

    def __init__(self, callback_data_prefix: Optional[str] = None):
        super().__init__()
        self.callback_data_prefix = callback_data_prefix

    def filter(self, message: telegram.Message) -> bool:
        reply_to = message.reply_to_message
        if reply_to and reply_to.from_user.is_bot and reply_to.from_user.id == get_running_app().bot.id:
            if self.callback_data_prefix:
                markup = reply_to.reply_markup
                if markup is None:
                    return False
                for line in markup.inline_keyboard:
                    for button in line:
                        data = button.callback_data and str(button.callback_data)
                        if not data or not data.startswith(self.callback_data_prefix):
                            return False
            return True
        return False
