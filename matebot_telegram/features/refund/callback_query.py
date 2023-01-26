"""
MateBot callback query for the refund command
"""

from typing import Awaitable, Callable

import telegram

from matebot_sdk import exceptions, schemas

from ..base import BaseCallbackQuery, ExtendedContext


class RefundCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /refund
    """

    def __init__(self):
        super().__init__(
            "refund",
            "^refund",
            {
                "approve": self.approve,
                "disapprove": self.disapprove,
                "abort": self.abort
            }
        )

    async def _handle_add_vote(
            self,
            update: telegram.Update,
            issuer: schemas.User,
            update_coroutine: Callable[[int, schemas.User], Awaitable[schemas.RefundVoteResponse]],
            data: str
    ) -> None:
        """
        Handle the vouching behavior for refunds, where the ``update_coroutine``
        argument is the SDK method to approve or disapprove a single refund
        and the ``user`` is the issuer of the command
        """

        _, refund_id = data.split(" ")
        refund_id = int(refund_id)

        response = await update_coroutine(refund_id, issuer)
        await update.callback_query.answer(
            f"You successfully voted {('against', 'for')[response.vote.vote]} the request."
        )

        text = await get_text(None, response.refund)
        keyboard = get_keyboard(response.refund)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.REFUND,
            refund_id,
            text,
            logger=self.logger,
            keyboard=keyboard
        )

    async def approve(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle a user event to approve a certain refund request
        """

        issuer = await context.application.client.get_core_user(update.callback_query.from_user)
        return await self._handle_add_vote(update, issuer, context.application.client.approve_refund, data)

    async def disapprove(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle a user event to disapprove a certain refund request
        """

        issuer = await context.application.client.get_core_user(update.callback_query.from_user)
        return await self._handle_add_vote(update, issuer, context.application.client.disapprove_refund, data)

    async def abort(self, update: telegram.Update, context: ExtendedContext, data: str) -> None:
        """
        Handle a user event to abort a certain refund request
        """

        _, refund_id = data.split(" ")
        refund_id = int(refund_id)

        issuer = await context.application.client.get_core_user(update.callback_query.from_user)
        try:
            refund = await context.application.client.abort_refund(refund_id, issuer)
        except exceptions.APIException as exc:
            await update.callback_query.answer(exc.message, show_alert=True)
            return

        text = await get_text(None, refund)
        keyboard = get_keyboard(refund)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.REFUND,
            refund.id,
            text,
            logger=self.logger,
            keyboard=keyboard,
            delete_shared_messages=True,
            job_queue=context.application.job_queue
        )
        await update.callback_query.answer()
