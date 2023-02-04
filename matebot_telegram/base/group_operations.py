"""
Helper utilities for classes that implement group operations

A group operation is currently only a communism, poll or refund.
"""

import asyncio
import logging
from typing import TypeVar

import telegram.ext

from ._common import ExtendedContext
from .. import shared_messages


GroupOpType = TypeVar("GroupOpType")  # examples: communism, poll, refund


async def new(
        obj: GroupOpType,
        share_type: shared_messages.ShareType,
        context: ExtendedContext,
        text: str,
        keyboard: telegram.InlineKeyboardMarkup,
        reply_message: telegram.Message,
        logger: logging.Logger
):
    """
    Create a new group operation and send out automatically shared messages

    A group operation is currently only a communism, poll or refund.
    """

    message: telegram.Message = await reply_message.reply_markdown(text, reply_markup=keyboard)
    if not context.application.client.shared_messages.add_message_by(
            share_type,
            obj.id,
            message.chat_id,
            message.message_id
    ):
        logger.error(f"Failed to add shared message for {share_type} {obj.id}: {message.to_dict()}")

    await context.application.send_auto_share_messages(
        share_type,
        obj.id,
        text,
        logger=logger,
        keyboard=keyboard,
        excluded=[message.chat_id]
    )


async def show(
        obj: GroupOpType,
        share_type: shared_messages.ShareType,
        context: ExtendedContext,
        text: str,
        keyboard: telegram.InlineKeyboardMarkup,
        reply_message: telegram.Message,
        logger: logging.Logger
):
    """
    Implement the 'show' subcommand for a group operation and handle outdated shared messages in the same chat

    A group operation is currently only a communism, poll or refund.
    """

    new_message = await reply_message.reply_markdown(text, reply_markup=keyboard)

    async def _edit(m: shared_messages.SharedMessage):
        try:
            edited_message: telegram.Message = await context.bot.edit_message_text(
                "\n\n".join(
                    text.split("\n\n")[:-1]
                    + ["_This message has been invalidated. Use the updated "
                       f"message below to interact with this {share_type.value}._"]
                ),
                m.chat_id,
                m.message_id,
                parse_mode=telegram.constants.ParseMode.MARKDOWN
            )
        except telegram.error.TelegramError as exc:
            logger.warning(f"Failed to edit shared msg of {share_type} {obj.id}: {type(exc).__name__}: {exc!s}")
        else:
            context.application.client.shared_messages.delete_message_by(
                shared_messages.ShareType.COMMUNISM,
                obj.id,
                edited_message.chat_id,
                edited_message.message_id
            )

    coroutines = [
        _edit(message) for message in context.application.client.shared_messages.get_messages(share_type, obj.id)
        if message.chat_id != new_message.chat_id
    ]
    context.application.client.shared_messages.add_message_by(
        shared_messages.ShareType.COMMUNISM,
        obj.id,
        new_message.chat_id,
        new_message.message_id
    )
    if coroutines:
        logger.debug(f"Updating {len(coroutines)} old messages in the current chat {new_message.chat_id} ...")
        await asyncio.gather(*coroutines)
