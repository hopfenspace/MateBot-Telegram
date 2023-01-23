"""
Private helpers for group operations of the Telegram MateBot
"""

import logging
from typing import Awaitable, Callable, TypeVar

import telegram.ext
from matebot_sdk import exceptions

from matebot_sdk.exceptions import APIException, APIConnectionException

from .. import client, err, shared_messages, util
from ..context import ExtendedContext


T = TypeVar("T")
FUNC_ARG_TYPE = TypeVar("FUNC_ARG_TYPE")
FUNC_ARG_RETURN_TYPE = TypeVar("FUNC_ARG_RETURN_TYPE")


async def new_group_operation(
        awaitable: Awaitable[T],
        sdk: client.AsyncMateBotSDKForTelegram,
        get_text: Callable[[T], Awaitable[str]],
        get_keyboard: Callable[[T], telegram.InlineKeyboardMarkup],
        reply_message: telegram.Message,
        share_type: shared_messages.ShareType,
        logger: logging.Logger,
        send_auto_shared_messages: bool = True
):
    """
    Create a new group operation and send out auto-shared messages

    A group operation is currently only a communism, poll or refund.
    """

    try:
        result = await awaitable
    except exceptions.APIException as exc:
        await reply_message.reply_text(exc.message)
        return

    text = await get_text(result)
    keyboard = get_keyboard(result)

    message: telegram.Message = await util.safe_call(
        lambda: reply_message.reply_markdown(text, reply_markup=keyboard),
        lambda: reply_message.reply_text(text, reply_markup=keyboard),
        use_result=True
    )
    if not sdk.shared_messages.add_message_by(share_type, result.id, message.chat_id, message.message_id):
        logger.error(f"Failed to add shared message for {share_type} {result.id}: {message.to_dict()}")

    if send_auto_shared_messages:
        await util.send_auto_share_messages(
            sdk.bot,
            share_type,
            result.id,
            text,
            logger=logger,
            keyboard=keyboard,
            excluded=[message.chat_id],
            job_queue=sdk.job_queue
        )


async def show_updated_group_operation(
        sdk: client.AsyncMateBotSDKForTelegram,
        msg: telegram.Message,
        text: str,
        keyboard: telegram.InlineKeyboardMarkup,
        share_type: shared_messages.ShareType,
        operation_id: int,
        logger: logging.Logger
):
    """
    Implement the 'show' subcommand for a group operation handle shared messages

    A group operation is currently only a communism or refund. Polls don't support 'show'.
    """

    new_message = await util.safe_call(
        lambda: msg.reply_markdown(text, reply_markup=keyboard),
        lambda: msg.reply_text(text, reply_markup=keyboard),
        use_result=True
    )

    for message in sdk.shared_messages.get_messages(share_type, operation_id):
        if message.chat_id != new_message.chat_id:
            continue

        try:
            edited_message: telegram.Message = await util.safe_call(
                lambda: msg.bot.edit_message_text(
                    "\n\n".join(
                        text.split("\n\n")[:-1]
                        + ["_This message has been invalidated. Use the updated "
                           f"message below to interact with this {share_type.value}._"]
                    ),
                    message.chat_id,
                    message.message_id,
                    parse_mode=telegram.constants.ParseMode.MARKDOWN
                ),
                lambda: msg.bot.edit_message_text(
                    "\n\n".join(
                        text.split("\n\n")[:-1]
                        + ["_This message has been invalidated. Use the updated "
                           f"message below to interact with this {share_type.value}._"]
                    ),
                    message.chat_id,
                    message.message_id
                ),
                use_result=True
            )
        except telegram.error.TelegramError as exc:
            logger.warning(f"Failed to edit shared msg of {share_type} {operation_id}: {type(exc).__name__}: {exc!s}")
        else:
            sdk.shared_messages.delete_message_by(
                shared_messages.ShareType.COMMUNISM,
                operation_id,
                edited_message.chat_id,
                edited_message.message_id
            )

    sdk.shared_messages.add_message_by(
        shared_messages.ShareType.COMMUNISM,
        operation_id,
        new_message.chat_id,
        new_message.message_id
    )


def get_voting_keyboard_for(name: str, object_id: int) -> telegram.InlineKeyboardMarkup:
    """
    Produce a voting keyboard for a group operation

    A group operation is currently only a communism, poll or refund.
    """

    return telegram.InlineKeyboardMarkup([
        [
            telegram.InlineKeyboardButton("APPROVE", callback_data=f"{name} approve {object_id}"),
            telegram.InlineKeyboardButton("DISAPPROVE", callback_data=f"{name} disapprove {object_id}"),
        ],
        [
            telegram.InlineKeyboardButton("FORWARD", callback_data=f"forward {name} {object_id} ask -1"),
            telegram.InlineKeyboardButton("ABORT", callback_data=f"{name} abort {object_id}")
        ]
    ])


class CommonBase:
    """
    Common base class providing a run wrapper that catches and handles various exceptions
    """

    logger: logging.Logger

    def __init__(self, logger: logging.Logger):
        self.logger: logging.Logger = logger

    async def _run(
            self,
            func: Callable[[FUNC_ARG_TYPE], Awaitable[FUNC_ARG_RETURN_TYPE]],
            reply: Callable[[str], Awaitable[None]],
            *args: FUNC_ARG_TYPE
    ) -> FUNC_ARG_RETURN_TYPE:
        """
        Execute the given coroutine with the specified arguments, using the reply coroutine for error reporting
        """

        try:
            return await func(*args)

        except APIConnectionException as exc:
            self.logger.exception(f"API connectivity problem @ {type(self).__name__} ({exc.exc})")
            await reply("There are temporary networking problems. Please try again later.")

        except APIException as exc:
            self.logger.warning(
                f"APIException @ {type(self).__name__} ({exc.status}, {exc.details}): {exc.message!r}",
                exc_info=exc.status != 400
            )
            await reply(exc.message)

        except err.MateBotException as exc:
            msg = str(exc)
            self.logger.debug(f"Uncaught MateBotException will now be replied to user: {msg!r}")
            await reply(msg)
