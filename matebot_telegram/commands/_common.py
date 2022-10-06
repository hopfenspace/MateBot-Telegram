import logging
from typing import Awaitable, Callable, TypeVar

import telegram
from matebot_sdk import exceptions

from .. import client, shared_messages, util


T = TypeVar("T")


async def new_group_operation(
        update: telegram.Update,
        awaitable: Awaitable[T],
        sdk: client.AsyncMateBotSDKForTelegram,
        get_text: Callable[[T], Awaitable[str]],
        get_keyboard: Callable[[T], telegram.InlineKeyboardMarkup],
        share_type: shared_messages.ShareType,
        logger: logging.Logger
):
    try:
        result = await awaitable
    except exceptions.APIException as exc:
        update.effective_message.reply_text(exc.message)
        return

    text = await get_text(result)
    keyboard = get_keyboard(result)

    message: telegram.Message = util.safe_call(
        lambda: update.effective_message.reply_markdown(text, reply_markup=keyboard),
        lambda: update.effective_message.reply_text(text, reply_markup=keyboard),
        use_result=True
    )
    if not sdk.shared_messages.add_message_by(share_type, result.id, message.chat_id, message.message_id):
        logger.error(f"Failed to add shared message for {share_type} {result.id}: {message.to_dict()}")

    util.send_auto_share_messages(
        update.effective_message.bot,
        share_type,
        result.id,
        text,
        logger=logger,
        keyboard=keyboard,
        excluded=[message.chat_id],
        job_queue=sdk.job_queue
    )
