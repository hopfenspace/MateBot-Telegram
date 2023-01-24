


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
            function: Callable[[int, schemas.User, ...], Awaitable[schemas.Communism]],
            delete: bool = False,
            **kwargs
    ) -> None:
        _, communism_id = self.data.split(" ")
        communism_id = int(communism_id)

        sender = await self.client.get_core_user(update.callback_query.from_user)
        communism = await function(communism_id, sender, **kwargs)

        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.COMMUNISM,
            communism.id,
            await get_text(self.client, communism),
            self.logger,
            get_keyboard(communism),
            telegram.ParseMode.MARKDOWN,
            delete_shared_messages=delete,
            job_queue=self.client.job_queue
        )

    async def join(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        await self._handle_update(update, self.client.increase_communism_participation, count=1)
        await update.callback_query.answer("You have joined the communism.")

    async def leave(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        await self._handle_update(update, self.client.decrease_communism_participation, count=1)
        await update.callback_query.answer("You have left the communism.")

    async def close(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        await self._handle_update(update, self.client.close_communism, delete=True)
        await update.callback_query.answer("The communism has been closed.")

    async def abort(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        await self._handle_update(update, self.client.abort_communism, delete=True)
        await update.callback_query.answer("The communism has been aborted.")
