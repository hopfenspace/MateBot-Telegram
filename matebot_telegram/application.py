"""
Extended Application to combine various MateBot Telegram core components in one place
"""

import logging
from typing import List, Optional, Union

import telegram.ext
import tornado.web

from . import api_callback, client as _client, config as _config, shared_messages as _shared_messages


class ExtendedApplication(telegram.ext.Application):
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
        self._api_event_handler_logger = logging.getLogger("mbt.api-event")

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
            disable_notification: bool = True,
            job_queue: bool = True
    ) -> bool:
        """
        Send shared messages automatically to a predefined list of recipients

        This feature is mainly used by the API callback implementations to
        inform a list of users about incoming events. It also tries to use the
        specified parse mode. The list of excluded users should be accurate to
        not send two messages to the same user (in case any user already
        received a separate message via some other channel or functionality).

        If the job queue is set to False, all messages will be sent out in
        order and will be awaited, which may slow down the calling function.
        Otherwise, all jobs will be created to be executed in the next seconds.

        Returns True for successful delivery (or queuing) of at least one
        message, False otherwise (including if no receivers are configured).
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

        async def _send(receiver_: Union[str, int]):
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
        for receiver in set(receivers):
            if receiver in [int(m.chat_id) for m in shared_messages] + excluded:
                continue
            if job_queue:
                self.job_queue.run_once(lambda: _send(receiver), 0)
            else:
                await _send(receiver)
        return True

    async def update_shared_messages(
            self,
            share_type: _shared_messages.ShareType,
            share_id: int,
            text: str,
            logger: Optional[logging.Logger] = None,
            keyboard: Optional[telegram.InlineKeyboardMarkup] = None,
            try_parse_mode: telegram.constants.ParseMode = telegram.constants.ParseMode.MARKDOWN,
            delete_shared_messages: bool = False,
            job_queue: bool = True
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

        If the job queue is set to False, all messages will be sent out in
        order and will be awaited, which may slow down the calling function.
        Otherwise, all jobs will be created to be executed in the next seconds.

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

        async def _handle_update(m: _shared_messages.SharedMessage):
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
        success = True
        for msg in msgs:
            if job_queue:
                self.job_queue.run_once(lambda: _handle_update(msg), 0)
            else:
                success = success and await _handle_update(msg)

        if job_queue:
            logger.debug("Detached calls to job queue, messages will be updated soon")
        else:
            if success:
                logger.debug("Successfully updated all shared messages")
            else:
                logger.warning(f"Failed to update at least one shared message for {share_type} {share_id}")
        return success


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
