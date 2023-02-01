"""
Extended Application to combine various MateBot Telegram core components in one place
"""

import asyncio
import logging
from typing import List, Optional, Union

import telegram.ext
import tornado.web

from . import api_callback, client as _client, config as _config, shared_messages as _shared_messages


class ExtendedApplication(telegram.ext.Application):
    """
    Extended version of PTB's Application class to combine various core components in one place

    Since the application is part of the context given to handler coroutines,
    the handlers can easily access the application and its attributes to access
    various program key components. Those components include the following:
     - a logger which may be used to create children (but not used directly)
     - the configured MateBot SDK instance which can be queried to
       interact with the core API server
     - the loaded program configuration for easier access without reloading
     - the dispatcher of API callback requests used to register new callback
       handlers via the ``dispatcher.register`` function
     - the callback server which is a HTTP server listening for incoming
       API callback requests to be forwarded to the dispatcher

    Additionally, it provides two convenient methods to handle shared messages.

    Do not create more than one instance of this class, since handling multiple
    SDK instances, callback servers and application listeners is not supported.
    """

    client: _client.AsyncMateBotSDKForTelegram
    config: _config.Configuration
    logger: logging.Logger
    dispatcher: api_callback.APICallbackDispatcher
    callback_server: tornado.web.HTTPServer

    def __init__(self, config: _config.Configuration, logger: logging.Logger, **kwargs):
        super().__init__(**kwargs)
        self.config = config
        self.logger = logger

        # Storing the logger here provides the advantage of easier changes if necessary
        # (the API callback handlers should therefore use `app.event_logger` for logging)
        self._api_event_handler_logger = self.logger.getChild("api-event")

        self.client = None  # noqa, the client has to be set in the post_init method
        self.dispatcher = None  # noqa, the dispatcher has to be set in the post_init method
        self.callback_server = None  # noqa, the callback server has to be set in the post_init method

        global _running_app
        if _running_app is not None:
            self.logger.warning(
                "Multiple applications have been registered. This is NOT supported and may lead "
                "to any type of errors, including race conditions, undefined behavior and crashes."
            )
        else:
            _running_app = self

    @property
    def event_logger(self) -> logging.Logger:
        return self._api_event_handler_logger

    async def send_auto_share_messages(
            self,
            share_type: _shared_messages.ShareType,
            share_id: int,
            text: str,
            logger: Optional[logging.Logger] = None,
            keyboard: Optional[telegram.InlineKeyboardMarkup] = None,
            excluded: List[int] = None,
            try_parse_mode: telegram.constants.ParseMode = telegram.constants.ParseMode.MARKDOWN,
            disable_notification: bool = True
    ) -> bool:
        """
        Send shared messages automatically to a predefined list of recipients

        This feature is mainly used by the API callback implementations to
        inform a list of users about incoming events. It also tries to use the
        specified parse mode. The list of excluded users should be accurate to
        not send two messages to the same user (in case any user already
        received a separate message via some other channel or functionality).

        Returns True for successful delivery of all the expected messages,
        False otherwise (including if no receivers are configured).
        """

        if logger is None:
            logger = self.logger.getChild(share_type.value)
        if not hasattr(self.config.auto_forward, share_type.value):
            logger.warning(f"No auto-forward rules defined for {share_type}!")
            return False

        excluded = excluded or []
        receivers = getattr(self.config.auto_forward, share_type.value)
        logger.debug(f"Configured receivers of {share_type} ({share_id}) auto-forward: {receivers}")
        if receivers is None:
            return False

        async def _send(receiver_: Union[str, int]) -> None:
            logger.debug(f"Trying to send message for {share_type} ({share_id}) to {receiver_!r} ...")
            message = await self.bot.send_message(
                chat_id=receiver_,
                text=text,
                parse_mode=try_parse_mode,
                disable_notification=disable_notification,
                reply_markup=keyboard
            )
            self.client.shared_messages.add_message_by(share_type, share_id, message.chat_id, message.message_id)
            logger.debug(f"Added message {message.message_id} in chat {message.chat_id} to {share_type} ({share_id})")

        shared_messages = self.client.shared_messages.get_messages(share_type, share_id)
        coroutines = []
        for receiver in set(receivers):
            if receiver in [int(m.chat_id) for m in shared_messages] + excluded:
                continue
            coroutines.append(_send(receiver))
        errors = [obj for obj in await asyncio.gather(*coroutines, return_exceptions=True) if obj is not None]
        for err in errors:
            self.logger.error(
                f"Sending didn't complete successfully for 'send_auto_share_messages' with {share_type} {share_id}",
                exc_info=err
            )
        return len(errors) == 0

    async def update_shared_messages(
            self,
            share_type: _shared_messages.ShareType,
            share_id: int,
            text: str,
            logger: Optional[logging.Logger] = None,
            keyboard: Optional[telegram.InlineKeyboardMarkup] = None,
            try_parse_mode: telegram.constants.ParseMode = telegram.constants.ParseMode.MARKDOWN,
            delete_shared_messages: bool = False
    ) -> bool:
        """
        Update all shared messages of a given share type and ID with some text

        This feature is mainly used by the API callback implementations to
        update the shared messages based on incoming events. It also tries to
        use the specified parse mode. If the switch to delete shared messages
        is set, the entry for the just edited message is dropped from the
        database (the Telegram message will be edited with the specified text,
        not deleted!). This prevents duplicate and outdated shared messages
        if a group operation (e.g., a communism) is closed or aborted.

        Returns True if no error occurred while sending or parsing messages.
        """

        if logger is None:
            logger = self.logger.getChild(share_type.value)

        async def _edit_msg(**kwargs):
            try:
                await self.bot.edit_message_text(text=text, **kwargs)
            except telegram.error.BadRequest as exc:
                if not str(exc).startswith("Message is not modified: specified new message content"):
                    raise

        async def _handle_update(m: _shared_messages.SharedMessage) -> None:
            logger.debug(f"Trying to edit message {m.message_id} in chat {m.chat_id} by {share_type} ({share_id}) ...")
            await _edit_msg(
                chat_id=m.chat_id,
                message_id=m.message_id,
                parse_mode=try_parse_mode,
                reply_markup=keyboard
            )
            logger.debug(f"Updated message {m.message_id} in chat {m.chat_id} by {share_type} ({share_id})")
            if delete_shared_messages:
                self.client.shared_messages.delete_message_by(m.share_type, m.share_id, m.chat_id, m.message_id)
                logger.debug(f"Dropped the shared message entry for {share_type} {share_id}")

        msgs = self.client.shared_messages.get_messages(share_type, share_id)
        logger.debug(f"Found {len(msgs)} shared messages for {share_type} ({share_id})")
        coroutines = [_handle_update(msg) for msg in msgs]
        errors = [obj for obj in await asyncio.gather(*coroutines, return_exceptions=True) if obj is not None]
        for err in errors:
            self.logger.error(
                f"Sending didn't complete successfully for 'send_auto_share_messages' with {share_type} {share_id}",
                exc_info=err
            )
        if len(errors) == 0:
            self.logger.debug("No errors encountered while editing the shared messages")
        return len(errors) == 0


# Global variables are discouraged but currently required to allow
# access of subsystems like the parser and the commands, which
# dynamically use attributes of the application (usually not
# the application's methods that interact with Telegram). However,
# those subsystems must always use the getter function below
_running_app: Optional[ExtendedApplication] = None


def get_running_app() -> Optional[ExtendedApplication]:
    """
    Return the currently running ExtendedApplication, if any
    """

    return _running_app
