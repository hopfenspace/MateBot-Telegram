"""
Private helpers for group operations of the Telegram MateBot
"""

import logging
from typing import Awaitable, Callable, TypeVar

import telegram.ext
from matebot_sdk import exceptions

from .. import client, shared_messages, util


T = TypeVar("T")


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
