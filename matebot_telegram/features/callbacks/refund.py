
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
            get_client_func: Callable[[int, schemas.User], Awaitable[schemas.RefundVoteResponse]]
    ) -> None:
        _, refund_id = self.data.split(" ")
        refund_id = int(refund_id)

        user = await self.client.get_core_user(update.callback_query.from_user)
        response = await get_client_func(refund_id, user)
        await update.callback_query.answer(f"You successfully voted {('against', 'for')[response.vote.vote]} the request.")

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

    async def approve(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_add_vote(update, self.client.approve_refund)

    async def disapprove(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_add_vote(update, self.client.disapprove_refund)

    async def abort(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, refund_id = self.data.split(" ")
        refund_id = int(refund_id)

        issuer = await self.client.get_core_user(update.callback_query.from_user)
        try:
            refund = await self.client.abort_refund(refund_id, issuer)
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
            job_queue=self.client.job_queue
        )
        await update.callback_query.answer()
