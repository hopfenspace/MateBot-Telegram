"""
MateBot callback query handler for the poll command
"""

from typing import Awaitable, Callable

import telegram
from matebot_sdk import exceptions, schemas

from . import common
from ... import shared_messages
from ...base import BaseCallbackQuery, ExtendedContext, group_operations


class PollCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /poll
    """

    def __init__(self):
        super().__init__(
            "poll",
            "^poll",
            {
                "dont-open": self.dont_open,
                "new": self.new,
                "approve": self.approve,
                "disapprove": self.approve,
                "abort": self.abort
            }
        )

    async def dont_open(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        TODO
        """

        _, _, _, original_sender = data.split(" ")
        if update.callback_query.from_user.id != int(original_sender):
            await update.callback_query.answer("Only the creator of this poll request can use it!")
            return
        self.logger.debug("No poll should be opened right now")
        await update.callback_query.message.edit_text("You chose not to open a poll right now.", reply_markup=None)
        context.drop_callback_data(update.callback_query)
        await update.callback_query.answer("No poll has been opened")

    async def new(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Create a new poll of a specified type
        """

        _, affected_user, poll_type, original_sender = data.split(" ")
        affected_user = int(affected_user)
        original_sender = int(original_sender)
        poll_type = schemas.PollVariant(poll_type)

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer("Only the creator of this poll request can alter it!")
            return

        user = (await context.application.client.get_users(affected_user))[0]
        issuer = await context.application.client.get_core_user(update.callback_query.from_user)
        poll = await context.application.client.create_poll(affected_user, issuer, poll_type)
        await group_operations.new(
            poll,
            shared_messages.ShareType.POLL,
            context,
            await common.get_text(context.application.client, poll),
            common.get_keyboard(poll),
            update.callback_query.message,
            self.logger
        )
        await update.callback_query.message.edit_text(
            f"You have selected the poll type for the new poll about the user {user.name}.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )

    async def _handle_vote(
            self,
            update: telegram.Update,
            context: ExtendedContext,
            data: str,
            get_client_func: Callable[[int, schemas.User], Awaitable[schemas.PollVoteResponse]]
    ) -> None:
        poll_id = int(data.split(" ")[-1])

        user = await context.application.client.get_core_user(update.callback_query.from_user)
        response = await get_client_func(poll_id, user)
        await update.callback_query.answer(f"You successfully voted {('against', 'for')[response.vote.vote]} the request.")

        text = await common.get_text(context.application.client, response.poll)
        keyboard = common.get_keyboard(response.poll)
        await context.application.update_shared_messages(
            shared_messages.ShareType.POLL,
            poll_id,
            text,
            logger=self.logger,
            keyboard=keyboard
        )

    async def approve(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        TODO
        """

        return await self._handle_vote(update, context, data, context.application.client.approve_poll)

    async def disapprove(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        TODO
        """

        return await self._handle_vote(update, context, data, context.application.client.disapprove_poll)

    async def abort(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        TODO
        """

        _, poll_id = data.split(" ")
        poll_id = int(poll_id)

        issuer = await context.application.client.get_core_user(update.callback_query.from_user)
        try:
            poll = await context.application.client.abort_poll(poll_id, issuer)
        except exceptions.APIException as exc:
            await update.callback_query.answer(exc.message, show_alert=True)
            return

        text = await common.get_text(context.application.client, poll)
        keyboard = common.get_keyboard(poll)
        await context.application.update_shared_messages(
            shared_messages.ShareType.POLL,
            poll.id,
            text,
            logger=self.logger,
            keyboard=keyboard,
            delete_shared_messages=True
        )
        await update.callback_query.answer()
