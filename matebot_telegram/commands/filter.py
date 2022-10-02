"""
MateBot's special Telegram update filter collection
"""

from typing import Optional

import telegram.ext

from .. import client


class ReplyMessageHandlerFilter(telegram.ext.UpdateFilter):
    """
    Update filter to only allow messages which are a reply to a message from the bot

    Optionally restricts those messages to must contain a callback inline keyboard,
    where all available buttons have a known common command prefix.
    """

    def __init__(self, allow_edits: bool, callback_data_prefix: Optional[str] = None):
        self.allow_edits = allow_edits
        self.callback_data_prefix = callback_data_prefix

    def filter(self, update: telegram.Update) -> bool:
        if update.effective_message is None or (update.edited_message is not None and not self.allow_edits):
            return False
        reply_to = update.effective_message.reply_to_message
        if reply_to and reply_to.from_user.is_bot and reply_to.from_user.id == client.client.bot.id:
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
