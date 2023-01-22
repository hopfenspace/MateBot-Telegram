"""
MateBot inline query executors to forward collective operations
"""

import re

import telegram.ext

from matebot_sdk import exceptions, schemas

from . import communism, polls, refund
from .. import client, err, shared_messages, util
from ..base import BaseCallbackQuery, BaseMessage


class ForwardCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for forwarding collective operations

    The callback query data for this class has five components joined by spaces:
     - "forward" to identify this callback query type
     - "communism"|"poll"|refund" to identify the collective operation type
     - {int} as ID of the respective collective to identify it safely
     - "abort"|"ask" as the operation of the forwarding process
       - "abort" to delete the message of the bot (with origin user verification)
       - "ask" will respond with a short notice that the user has to answer this bot
         directly together with the abort button (which is also used for identification)
     - {int}|"-1" to verify the sender of the reply message to the query ("-1" if not available)
    """

    DATA_REGEX: re.Pattern = re.compile(r"^(communism|poll|refund) (\d+) (abort|ask) ((?<=abort )\d+|(?<=ask )-1)$")

    def __init__(self):
        super().__init__(
            "forward",
            "^forward",
            {"": self.handle}
        )

    async def handle(self, update: telegram.Update) -> None:
        cb = update.callback_query
        match = self.DATA_REGEX.match(self.data)
        if not match:
            self.logger.debug(f"Unknown forward callback query ignored: {self.data!r}")
            cb.answer()
            return
        collective_type, collective_id, cmd, user_id = match.groups()
        collective_id, user_id = int(collective_id), int(user_id)

        getter = {
            "communism": self.client.get_communisms,
            "poll": self.client.get_polls,
            "refund": self.client.get_refunds
        }[collective_type]
        collectives = await getter(id=collective_id, active=True)
        if len(collectives) != 1:
            cb.answer()
            return

        if cmd == "abort":
            if cb.from_user.id != user_id:
                cb.answer("You are not permitted to perform this operation.", show_alert=True)
                return
            cb.delete_message()
        elif cmd == "ask":
            cb.message.reply_text(
                f"Do you want to share this {collective_type} with somebody who doesn't have access to this chat? "
                f"Just reply to this message with the username and the {collective_type} will be forwarded privately.",
                reply_markup=telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton(
                    f"Don't forward this {collective_type}",
                    callback_data=f"forward {collective_type} {collective_id} abort {cb.from_user.id}"
                )]])
            )
            cb.answer()


class ForwardReplyMessage(BaseMessage):
    """
    Handler for dynamic forward reply messages, i.e. users replying to forward requests with a username
    """

    DATA_REGEX: re.Pattern = re.compile(r"^forward (communism|poll|refund) (\d+) (abort) (\d+)$")

    def __init__(self):
        super().__init__("forward")

    async def run(self, msg: telegram.Message, context: telegram.ext.CallbackContext) -> None:
        if msg.reply_to_message is None:
            self.logger.error("ForwardReply doesn't have a reply_to_message, see msg below (debug)")
            self.logger.debug(str(msg))
            return
        keyboard = msg.reply_to_message.reply_markup.inline_keyboard
        if len(keyboard) != 1 or len(keyboard[0]) != 1:
            # This is not the expected message the user is replying to, since the correct message would have one button
            return
        data = str(keyboard[0][0].callback_data)
        match = self.DATA_REGEX.match(data)
        if not match:
            self.logger.warning(f"Badly formatted callback data for forward reply message handler: {data!r}")
            return
        collective_type, collective_id, _, user_id = match.groups()
        collective_id, user_id = int(collective_id), int(user_id)
        if msg.from_user.id != user_id:
            return

        # It's ensured it's the correct user and all relevant data is known, now try to get the active collective
        getter = {
            "communism": self.client.get_communisms,
            "poll": self.client.get_polls,
            "refund": self.client.get_refunds
        }[collective_type]
        collectives = await getter(id=collective_id, active=True)
        if len(collectives) != 1:
            self.logger.warning(f"{collective_type} {collective_id} wasn't found during forward reply message handling")
            msg.reply_to_message.delete()
            return
        collective = collectives[0]

        # Search for the user referenced in the user's message
        try:
            core_user = await self.client.get_core_user(msg.text, foreign_user=True)
        except (err.MateBotException, exceptions.MateBotSDKException) as exc:
            self.logger.debug(f"During handling of the forward message {msg.text!r}: {exc!r}")
            msg.reply_text(str(exc))
            return
        telegram_user = self.client.find_telegram_user(core_user.id)
        if telegram_user is None:
            self.logger.debug(f"Core user {core_user.id} doesn't use this application; declining forwarding")
            msg.reply_text(
                f"Your search for {msg.text!r} found the user {core_user.name}. However, this user "
                f"is either not registered with this MateBot frontend or hasn't set up a shared account "
                f"on multiple applications. Therefore, forwarding this {collective_type} isn't possible."
            )
            msg.reply_to_message.delete()
            return

        new_message = msg.bot.send_message(telegram_user[0], f"Forwarding a new {collective_id} to you ...")

        if collective_type == "communism":
            collective: schemas.Communism
            client.client.shared_messages.add_message_by(
                shared_messages.ShareType.COMMUNISM,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            util.update_all_shared_messages(
                msg.bot,
                shared_messages.ShareType.COMMUNISM,
                collective_id,
                await communism.get_text(client.client, collective),
                keyboard=communism.get_keyboard(collective),
                job_queue=client.client.job_queue
            )
        elif collective_type == "poll":
            collective: schemas.Poll
            client.client.shared_messages.add_message_by(
                shared_messages.ShareType.POLL,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            util.update_all_shared_messages(
                client.client.bot,
                shared_messages.ShareType.POLL,
                collective_id,
                await polls.get_text(client.client, collective),
                keyboard=polls.get_keyboard(collective),
                job_queue=client.client.job_queue
            )
        elif collective_type == "refund":
            collective: schemas.Refund
            client.client.shared_messages.add_message_by(
                shared_messages.ShareType.REFUND,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            util.update_all_shared_messages(
                client.client.bot,
                shared_messages.ShareType.REFUND,
                collective_id,
                await refund.get_text(None, collective),
                keyboard=refund.get_keyboard(collective),
                job_queue=client.client.job_queue
            )
        msg.reply_to_message.edit_text(
            f"This {collective_type} is forwarded to {core_user.name} ...",
            reply_markup=None
        )
