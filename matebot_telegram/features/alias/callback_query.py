
class AliasCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for newly created aliases
    """

    def __init__(self):
        super().__init__(
            "alias",
            "^alias",
            {
                "accept": self.accept,
                "deny": self.deny,
                "report": self.report,
                "clear": self.clear
            }
        )

    @staticmethod
    async def clear(update: telegram.Update) -> None:
        msg = update.callback_query.message
        if msg is not None:
            await update.callback_query.message.edit_text("This message has been cleared.", reply_markup=None)
        await update.callback_query.answer()

    async def _get_alias_and_user(self, update: telegram) -> Optional[Tuple[schemas.Alias, schemas.User]]:
        _, alias_id, original_sender = self.data.split(" ")
        original_sender = int(original_sender)
        if update.callback_query.from_user.id != original_sender:
            await update.callback_query.answer("Only the account owner of this request can confirm it!", show_alert=True)
            return

        issuer = await self.client.get_core_user(update.callback_query.from_user)
        aliases = await self.client.get_aliases(id=int(alias_id))
        if len(aliases) != 1:
            self.logger.warning(f"Invalid alias ID {alias_id}")
            return

        if aliases[0].user_id != issuer.id:
            await update.callback_query.answer("Only owner of the account can answer this question!", show_alert=True)
            return
        return aliases[0], issuer

    async def accept(self, update: telegram.Update) -> None:
        result = await self._get_alias_and_user(update)
        if not result:
            return
        alias, user = result

        alias = await self.client.confirm_alias(alias, user)
        apps = await self.client.get_applications(id=alias.application_id)
        if len(apps) != 1:
            self.logger.warning(f"Invalid response with {len(apps)} results instead of exactly one")
            return
        msg = f"You successfully confirmed the alias {alias.username} of the application {apps[0].name}. " \
              f"Your accounts are now linked together and will use the same balance, permissions etc."
        await update.callback_query.message.edit_text(msg, reply_markup=telegram.InlineKeyboardMarkup([]))
        self.client.shared_messages.delete_messages(shared_messages.ShareType.ALIAS, alias.id)

    async def deny(self, update: telegram.Update) -> None:
        result = await self._get_alias_and_user(update)
        if not result:
            return
        alias, user = result

        deletion = await self.client.delete_alias(alias, user)
        await update.callback_query.message.edit_text(
            "The alias has been deleted. It won't be possible to use it in the future.\n"
            f"You have {len(deletion.aliases)} registered aliases for your account.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
        self.client.shared_messages.delete_messages(shared_messages.ShareType.ALIAS, alias.id)

    async def report(self, update: telegram.Update) -> None:
        raise NotImplementedError
        # result = await self._get_alias_and_user(update)
        # if not result:
        #     return
        # alias, user = result
        #
        # msg = (
        #     f"Spam reported in chat {update.effective_chat.id} by {update.effective_user.name} "
        #     f"({update.effective_user.id}) for the new alias {alias.id} ({alias.dict()})! "
        #     f"Please determine the source of this newly created alias."
        # )
        # self.logger.warning(msg)
        # for receiver in config["chats"]["notification"]:
        #     await update.callback_query.bot.send_message(receiver, msg)
        #
        # await SDK.drop_alias(alias)
        # await update.callback_query.message.edit_text(
        #     "The alias has been deleted. It won't be possible to use it in the future.\nThanks for your report.",
        #     reply_markup=telegram.InlineKeyboardMarkup([])
        # )
        # self.client.shared_messages.delete_messages(shared_messages.ShareType.ALIAS, alias.id)
