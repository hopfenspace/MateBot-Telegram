"""
MateBot callback queries for the forwarding feature of group operations
"""

import telegram.ext

from .common import CALLBACK_REGEX
from ...base import BaseCallbackQuery, ExtendedContext


class ForwardCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for forwarding group operations

    See the description of the regular expression ``CALLBACK_REGEX`` for
    more details about the structure and workflow of this callback class.
    """

    def __init__(self):
        super().__init__(
            "forward",
            "^forward",
            {"": self.handle}
        )

    async def handle(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle the forward callback query according to the rules described in the class docs
        """

        cb = update.callback_query
        match = CALLBACK_REGEX.match(data)
        if not match:
            self.logger.debug(f"Unknown forward callback query ignored: {data!r}")
            await cb.answer()
            return
        collective_type, collective_id, cmd, user_id = match.groups()
        collective_id, user_id = int(collective_id), int(user_id)

        getter = {
            "communism": context.application.client.get_communisms,
            "poll": context.application.client.get_polls,
            "refund": context.application.client.get_refunds
        }[collective_type]
        collectives = await getter(id=collective_id, active=True)
        if len(collectives) != 1:
            await cb.answer(f"This {collective_type} is unknown or closed and can't be forwarded.")
            return

        if cmd == "abort":
            if cb.from_user.id != user_id:
                await cb.answer("You are not permitted to perform this operation!", show_alert=True)
                return
            await cb.delete_message()
        elif cmd == "ask":
            await cb.message.reply_text(
                f"Do you want to share this {collective_type} with somebody who doesn't have access to this chat? "
                f"Just reply to this message with the username and the {collective_type} will be forwarded privately.",
                reply_markup=telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton(
                    f"Don't forward this {collective_type}",
                    callback_data=f"forward {collective_type} {collective_id} abort {cb.from_user.id}"
                )]])
            )
            await cb.answer()
