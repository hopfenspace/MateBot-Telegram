"""
MateBot command executor class for /poll
"""

import time
import telegram
from typing import Awaitable, Callable, Optional

from matebot_sdk import exceptions, schemas

from . import common
from .. import client, shared_messages, util
from ..api_callback import application
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.types import any_user_type
from ..parsing.util import Namespace


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

    async def dont_open(self, update: telegram.Update) -> None:
        _, _, _, original_sender = self.data.split(" ")
        if update.callback_query.from_user.id != int(original_sender):
            await update.callback_query.answer("Only the creator of this poll request can use it!")
            return
        await update.callback_query.message.edit_text("You chose not to open a poll right now.", reply_markup=None)
        await update.callback_query.answer("No poll has been opened")

    async def new(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, affected_user, poll_type, original_sender = self.data.split(" ")
        affected_user = int(affected_user)
        original_sender = int(original_sender)
        poll_type = schemas.PollVariant(poll_type)

        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer("Only the creator of this poll request can alter it!")
            return

        user = (await self.client.get_users(affected_user))[0]
        issuer = await self.client.get_core_user(update.callback_query.from_user)
        await _common.new_group_operation(
            self.client.create_poll(affected_user, issuer, poll_type),
            self.client,
            lambda p: get_text(self.client, p),
            get_keyboard,
            update.callback_query.message,
            shared_messages.ShareType.POLL,
            self.logger
        )
        await update.callback_query.message.edit_text(
            f"You have selected the poll type for the new poll about the user {user.name}.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )

    async def _handle_vote(
            self,
            update: telegram.Update,
            get_client_func: Callable[[int, schemas.User], Awaitable[schemas.PollVoteResponse]]
    ) -> None:
        poll_id = int(self.data.split(" ")[-1])

        user = await self.client.get_core_user(update.callback_query.from_user)
        response = await get_client_func(poll_id, user)
        await update.callback_query.answer(f"You successfully voted {('against', 'for')[response.vote.vote]} the request.")

        text = await get_text(self.client, response.poll)
        keyboard = get_keyboard(response.poll)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.POLL,
            poll_id,
            text,
            logger=self.logger,
            keyboard=keyboard
        )

    async def approve(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_vote(update, self.client.approve_poll)

    async def disapprove(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_vote(update, self.client.disapprove_poll)

    async def abort(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, poll_id = self.data.split(" ")
        poll_id = int(poll_id)

        issuer = await self.client.get_core_user(update.callback_query.from_user)
        try:
            poll = await self.client.abort_poll(poll_id, issuer)
        except exceptions.APIException as exc:
            await update.callback_query.answer(exc.message, show_alert=True)
            return

        text = await get_text(self.client, poll)
        keyboard = get_keyboard(poll)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.POLL,
            poll.id,
            text,
            logger=self.logger,
            keyboard=keyboard,
            delete_shared_messages=True,
            job_queue=self.client.job_queue
        )
        await update.callback_query.answer()
