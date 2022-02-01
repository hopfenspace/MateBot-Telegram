"""
MateBot callback query handler for newly created aliases
"""

import logging
from typing import Tuple

import telegram
from matebot_sdk import schemas
from matebot_sdk.base import CallbackUpdate

from ..api_callback import dispatcher
from ..base import BaseCallbackQuery
from ..client import SDK
from ..config import config


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
                "report": self.report
            }
        )

    async def _get_alias_and_user(self, update: telegram) -> Tuple[schemas.Alias, schemas.User]:
        _, alias_id = self.data.split(" ")
        alias = await SDK.get_alias_by_id(int(alias_id))
        user = await SDK.get_user_by_app_alias(str(update.callback_query.from_user.id))

        if alias.user_id != user.id:
            update.callback_query.answer("Only owner of the account can answer this question!", show_alert=True)
            return tuple()
        return alias, user

    async def accept(self, update: telegram.Update) -> None:
        result = await self._get_alias_and_user(update)
        if not result:
            return
        alias, user = result

        alias = await SDK.confirm_alias(alias)
        app = await SDK.get_application_by_id(alias.application_id)
        msg = f"You successfully confirmed the alias {alias.app_username} of the application {app.name}. " \
              f"Your accounts are now linked together and will use the same balance, permissions etc."
        update.message.edit_text(msg, reply_markup=telegram.InlineKeyboardMarkup([]))

    async def deny(self, update: telegram.Update) -> None:
        result = await self._get_alias_and_user(update)
        if not result:
            return
        alias, user = result

        await SDK.drop_alias(alias)
        update.message.edit_text(
            "The alias has been deleted. It won't be possible to use it in the future.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )

    async def report(self, update: telegram.Update) -> None:
        result = await self._get_alias_and_user(update)
        if not result:
            return
        alias, user = result

        msg = (
            f"Spam reported in chat {update.effective_chat.id} by {update.effective_user.name} "
            f"({update.effective_user.id}) for the new alias {alias.id} ({alias.dict()})! "
            f"Please determine the source of this newly created alias."
        )
        self.logger.warning(msg)
        for receiver in config["chats"]["notifications"]:
            update.callback_query.bot.send_message(receiver, msg)

        await SDK.drop_alias(alias)
        update.message.edit_text(
            "The alias has been deleted. It won't be possible to use it in the future.\nThanks for your report.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )


async def _alias_callback_handler(method: CallbackUpdate, _: str, id_: int, bot: telegram.Bot, logger: logging.Logger):
    if method != method.CREATE:
        return

    app = await SDK.application
    alias = await SDK.get_alias_by_id(id_)
    other_app = await SDK.get_application_by_id(alias.application_id)
    user = await SDK.get_user_by_id(alias.user_id)
    app_aliases = [a for a in user.aliases if app.id == a.application_id and a.confirmed and a.unique]
    if not app_aliases:
        logger.debug(f"No confirmed unique app aliases found for {user}")
        return

    msg = (
        "Someone has just registered a new app alias using your existing account in another application. "
        "Currently, the other app alias is not confirmed and will therefore not be accepted for "
        "transactions or other operations.\nIf this alias was created by you, you need to ACCEPT it "
        "to connect your accounts successfully. If this wasn't you, please DENY this request.\n\n"
        f"Application ID: {alias.application_id}\n"
        f"Application name: {other_app.name}\n"
        f"Alias username: {alias.app_username}\n"
        f"Alias unique flag: {alias.unique}"
    )

    username = app_aliases[0].app_username
    bot.send_message(
        username if not username.isdigit() else int(username),
        msg,
        reply_markup=telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("ACCEPT", callback_data=f"alias accept {alias.id}"),
                telegram.InlineKeyboardButton("DENY", callback_data=f"alias deny {alias.id}"),
            ],
            [
                telegram.InlineKeyboardButton("DENY AND REPORT SPAM", callback_data=f"alias report {alias.id}"),
            ]
        ])
    )


dispatcher.register((CallbackUpdate.CREATE, "alias"), _alias_callback_handler)
dispatcher.register((CallbackUpdate.UPDATE, "alias"), _alias_callback_handler)
dispatcher.register((CallbackUpdate.DELETE, "alias"), _alias_callback_handler)
