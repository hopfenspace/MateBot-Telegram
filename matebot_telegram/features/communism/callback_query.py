"""
MateBot callback query handler for the communism command
"""

from typing import Awaitable, Callable

import telegram
from matebot_sdk import schemas

from . import common
from ... import shared_messages
from ...base import BaseCallbackQuery, ExtendedContext


class CommunismCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /communism
    """

    def __init__(self):
        super().__init__(
            "communism",
            "^communism",
            {
                "join": self.join,
                "leave": self.leave,
                "close": self.close,
                "abort": self.abort
            }
        )

    async def _handle_update(
            self,
            update: telegram.Update,
            context: ExtendedContext,
            data: str,
            function: Callable[[int, schemas.User, ...], Awaitable[schemas.Communism]],
            delete: bool = False,
            **kwargs
    ) -> None:
        _, communism_id = data.split(" ")
        communism_id = int(communism_id)

        sender = await context.application.client.get_core_user(update.callback_query.from_user)
        communism = await function(communism_id, sender, **kwargs)

        await context.application.update_shared_messages(
            shared_messages.ShareType.COMMUNISM,
            communism.id,
            await common.get_text(context.application.client, communism),
            self.logger,
            common.get_keyboard(communism),
            telegram.constants.ParseMode.MARKDOWN,
            delete_shared_messages=delete
        )

    async def join(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle the query of a user to join the communism (supports joining multiple times)
        """

        await self._handle_update(update, context, data, context.application.client.increase_communism_participation)
        await update.callback_query.answer("You have joined the communism.")

    async def leave(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle the query of a user to leave the communism
        """

        await self._handle_update(update, context, data, context.application.client.decrease_communism_participation)
        await update.callback_query.answer("You have left the communism.")

    async def close(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle the query to close (=accept) the communism
        """

        await self._handle_update(update, context, data, context.application.client.close_communism, delete=True)
        await update.callback_query.answer("The communism has been closed.")

    async def abort(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle the query to abort (=reject) the communism
        """

        await self._handle_update(update, context, data, context.application.client.abort_communism, delete=True)
        await update.callback_query.answer("The communism has been aborted.")
