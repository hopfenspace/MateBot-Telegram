"""
MateBot message handler for the forwarding feature of group operations
"""

from typing import Union

import telegram.ext
from matebot_sdk import exceptions, schemas

from .common import MESSAGE_CALLBACK_REGEX
from ..communism.common import get_text as get_communism_text, get_keyboard as get_communism_keyboard
from ..poll.common import get_text as get_poll_text, get_keyboard as get_poll_keyboard
from ..refund.common import get_text as get_refund_text, get_keyboard as get_refund_keyboard
from ... import shared_messages
from ...base import BaseMessage, err, ExtendedContext


class ForwardReplyMessage(BaseMessage):
    """
    Message handler for dynamic forward reply messages, i.e. users replying to forward requests with a username
    """

    def __init__(self):
        super().__init__("forward")

    async def run(self, msg: telegram.Message, context: ExtendedContext) -> None:
        if msg.reply_to_message is None:
            self.logger.error("ForwardReplyMessage doesn't have a reply_to_message, see debug message below")
            self.logger.debug(str(msg))
            return

        keyboard = msg.reply_to_message.reply_markup.inline_keyboard
        if len(keyboard) != 1 or len(keyboard[0]) != 1:
            # This is not the expected message the user is replying to, since the correct message would have one button
            return

        # See the description of the regular expression for more information about the query structure
        data = str(keyboard[0][0].callback_data)
        match = MESSAGE_CALLBACK_REGEX.match(data)
        if not match:
            self.logger.warning(f"Badly formatted callback data for forward reply message handler: {data!r}")
            return
        collective_type, collective_id, _, user_id = match.groups()
        collective_id, user_id = int(collective_id), int(user_id)
        if msg.from_user.id != user_id:
            return

        # It's ensured it's the correct user and all relevant data is known, now try to get the active collective
        getter = {
            "communism": context.application.client.get_communisms,
            "poll": context.application.client.get_polls,
            "refund": context.application.client.get_refunds
        }[collective_type]
        collectives = await getter(id=collective_id, active=True)
        if len(collectives) != 1:
            self.logger.warning(f"{collective_type} {collective_id} wasn't found during forward reply message handling")
            await msg.reply_text(f"Sorry, I can't forward this {collective_type}.")
            await msg.reply_to_message.delete()
            return
        collective: Union[schemas.Communism, schemas.Poll, schemas.Refund] = collectives[0]

        # Search for the user referenced in the user's message
        try:
            core_user = await context.application.client.get_core_user(msg.text, foreign_user=True)
        except (err.MateBotException, exceptions.MateBotSDKException) as exc:
            self.logger.debug(f"Error while handling the forward reply message {msg.text!r}: {exc!r}")
            await msg.reply_text(str(exc))
            return
        telegram_user = context.application.client.find_telegram_user(core_user.id)
        if telegram_user is None:
            self.logger.debug(f"Core user {core_user.id} doesn't use this application; declining forwarding")
            await msg.reply_text(
                f"Your search for {msg.text!r} found the user {core_user.name}. However, this user "
                f"is either not registered with this MateBot frontend or hasn't set up a shared account "
                f"on multiple applications. Therefore, forwarding this {collective_type} isn't possible."
            )
            await msg.reply_to_message.delete()
            return

        new_message = await context.bot.send_message(telegram_user[0], f"Forwarding a new {collective_id} to you ...")

        # Use the correct collective type to update the shared messages
        # TODO: Improve the block to be generic
        # TODO: Improve to not update all shared messages if just one has been added by this feature
        if collective_type == "communism":
            context.application.client.shared_messages.add_message_by(
                shared_messages.ShareType.COMMUNISM,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            await context.application.update_shared_messages(
                shared_messages.ShareType.COMMUNISM,
                collective_id,
                await get_communism_text(context.application.client, collective),
                self.logger,
                keyboard=get_communism_keyboard(collective)
            )
        elif collective_type == "poll":
            context.application.client.shared_messages.add_message_by(
                shared_messages.ShareType.POLL,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            await context.application.update_shared_messages(
                shared_messages.ShareType.POLL,
                collective_id,
                await get_poll_text(context.application.client, collective),
                self.logger,
                keyboard=get_poll_keyboard(collective)
            )
        elif collective_type == "refund":
            context.application.client.shared_messages.add_message_by(
                shared_messages.ShareType.REFUND,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            await context.application.update_shared_messages(
                shared_messages.ShareType.REFUND,
                collective_id,
                await get_refund_text(None, collective),
                self.logger,
                keyboard=get_refund_keyboard(collective)
            )

        await msg.reply_to_message.edit_text(
            f"This {collective_type} is forwarded to {core_user.name} ...",
            reply_markup=None
        )
