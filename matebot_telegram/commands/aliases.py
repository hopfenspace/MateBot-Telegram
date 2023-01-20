"""
MateBot callback query handler for newly created aliases
"""

import logging
from typing import List, Optional, Tuple

import telegram
from matebot_sdk import schemas

from .. import client, persistence, shared_messages, util
from ..api_callback import dispatcher
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.util import Namespace


def fmt_alias(alias: schemas.Alias, apps: List[schemas.Application]) -> str:
    state = "accepted" if alias.confirmed else "requested (!)"
    try:
        app = f"'{[a for a in apps if a.id == alias.application_id][0].name}'"
    except IndexError:
        app = f"app {alias.application_id}"
    return f"`ID {alias.id}: '{alias.username}' from {app}: {state}`"


class AliasCommand(BaseCommand):
    """
    Command executor for /alias
    """

    def __init__(self):
        super().__init__(
            "alias",
            "Manage your connected user accounts of other applications\n\n"
            "By default, this command shows you currently connected aliases, i.e. available "
            "logins from other applications that have access to your user account. There are "
            "a few subcommands available, e.g. `accept` to verify an alias and make it usable "
            "(because without verification, the connected user account can't be used for any "
            "actions) or `deny` to do the opposite and remove an alias.\nNote that you can't "
            "delete the alias of the currently used application (Telegram). To do this, you "
            "either need to use another application for the action or delete your whole user account."
        )
        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("accept", "deny", "show"),
            type=lambda x: str(x).lower()
        )

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if update.effective_chat.type != telegram.Chat.PRIVATE:
            update.effective_message.reply_text("You should execute this command in private chat only.")
            return

        user = await self.client.get_core_user(update.effective_message.from_user)
        if args.subcommand is None or args.subcommand == "show":
            aliases = await self.client.get_aliases(user_id=user.id)
            applications = await self.client.get_applications()
            msg = f"You currently have the following registered aliases:\n" \
                  + "\n".join([fmt_alias(alias, applications) for alias in aliases])
            util.safe_call(
                lambda: update.effective_message.reply_markdown_v2(msg),
                lambda: update.effective_message.reply_text(msg)
            )
        elif args.subcommand == "accept":
            aliases = await self.client.get_aliases(user_id=user.id, confirmed=False)
            if not aliases:
                update.effective_message.reply_text("Currently, you have no unconfirmed aliases.")
            else:
                msg = "Here's an overview of currently unconfirmed aliases. Clicking on the button will " \
                      "accept the respective alias and allows the owner of the app's account access to your " \
                      "user account. This includes making transactions, polls, communisms and other features."
                keyboard = [
                    [telegram.InlineKeyboardButton(
                        f"ID {alias.id}: '{alias.username}'",
                        callback_data=f"alias accept {alias.id} {update.effective_message.from_user.id}"
                    )]
                    for alias in aliases
                ] + [[telegram.InlineKeyboardButton("Don't accept any alias now", callback_data=f"alias clear")]]
                update.effective_message.reply_text(msg, reply_markup=telegram.InlineKeyboardMarkup(keyboard))
        elif args.subcommand == "deny":
            aliases = [
                a for a in await self.client.get_aliases(user_id=user.id)
                if a.application_id != client.client.app_id
            ]
            if not aliases:
                update.effective_message.reply_text(
                    "Currently, you have no aliases other than the Telegram alias. For safety "
                    "purposes, you can't delete the alias because it would lock you out of your "
                    "account. Use another account to delete the Telegram app alias."
                )
            else:
                msg = "Here's an overview of currently known aliases. Clicking on a button will remove " \
                      "the respective alias and deny the owner of the app's account further access to your " \
                      "user account. This includes making transactions, polls, communisms and other features.\n" \
                      "Note that the current app (Telegram) is not in the list, since deleting it would lock " \
                      "you out of your account. Use another frontend to delete the Telegram app."
                keyboard = [
                    [telegram.InlineKeyboardButton(
                        f"ID {alias.id}: '{alias.username}'",
                        callback_data=f"alias deny {alias.id} {update.effective_message.from_user.id}"
                    )]
                    for alias in aliases
                ] + [[telegram.InlineKeyboardButton("Don't deny any alias now", callback_data=f"alias clear")]]
                update.effective_message.reply_text(msg, reply_markup=telegram.InlineKeyboardMarkup(keyboard))


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
            update.callback_query.message.edit_text("This message has been cleared.", reply_markup=None)
        update.callback_query.answer()

    async def _get_alias_and_user(self, update: telegram) -> Optional[Tuple[schemas.Alias, schemas.User]]:
        _, alias_id, original_sender = self.data.split(" ")
        original_sender = int(original_sender)
        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer("Only the account owner of this request can confirm it!", show_alert=True)
            return

        issuer = await self.client.get_core_user(update.callback_query.from_user)
        aliases = await self.client.get_aliases(id=int(alias_id))
        if len(aliases) != 1:
            self.logger.warning(f"Invalid alias ID {alias_id}")
            return

        if aliases[0].user_id != issuer.id:
            update.callback_query.answer("Only owner of the account can answer this question!", show_alert=True)
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
        update.callback_query.message.edit_text(msg, reply_markup=telegram.InlineKeyboardMarkup([]))
        self.client.shared_messages.delete_messages(shared_messages.ShareType.ALIAS, alias.id)

    async def deny(self, update: telegram.Update) -> None:
        result = await self._get_alias_and_user(update)
        if not result:
            return
        alias, user = result

        deletion = await self.client.delete_alias(alias, user)
        update.callback_query.message.edit_text(
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
        #     update.callback_query.bot.send_message(receiver, msg)
        #
        # await SDK.drop_alias(alias)
        # update.callback_query.message.edit_text(
        #     "The alias has been deleted. It won't be possible to use it in the future.\nThanks for your report.",
        #     reply_markup=telegram.InlineKeyboardMarkup([])
        # )
        # self.client.shared_messages.delete_messages(shared_messages.ShareType.ALIAS, alias.id)


@dispatcher.register_for(schemas.EventType.ALIAS_CONFIRMATION_REQUESTED)
async def _handle_alias_confirmation_requested(event: schemas.Event):
    logger = logging.getLogger("api-callback.alias")
    aliases = await client.client.get_aliases(id=event.data["id"])
    if len(aliases) != 1:
        logger.warning(f"Confirmation request for invalid alias ID {event.data['id']}")
        return
    alias = aliases[0]
    if alias.confirmed:
        logger.debug(f"Alias ID {alias.id} for user ID {alias.user_id} is already confirmed")
        return

    if alias.application_id == client.client.app_id:
        logger.debug(f"Confirmation request for origin application ID {alias.application_id} ignored")
        return
    apps = await client.client.get_applications(id=alias.application_id)
    if len(apps) != 1:
        logger.error(f"Not exactly one app returned for call, found {len(apps)} objects")
        return
    app = apps[0]
    username = (await client.client.get_user(alias.user_id)).name
    user = client.client.find_telegram_user(alias.user_id)
    if not user:
        logger.debug("No telegram user found to notify for the newly created alias")
        return

    msg = (
        "Someone has just registered a new app alias using your existing account in another application. "
        "Currently, the other app alias is not confirmed and will therefore not be accepted for "
        "transactions or other operations.\nIf this alias was created by you, you need to ACCEPT it "
        "to connect your accounts successfully. You will then be able to use any of the confirmed "
        "registered applications interchangeably.\nIf this wasn't you, please DENY this request, "
        "which will also delete that newly created alias so it can't be activated in the future.\n\n"
        f"Application ID: {alias.application_id}\n"
        f"Application name: {app.name}\n"
        f"Creator username: {username}\n"
        f"Alias username: {alias.username}"
    )

    message = client.client.bot.send_message(
        user[0],
        msg,
        reply_markup=telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("ACCEPT", callback_data=f"alias accept {alias.id} {user[0]}"),
                telegram.InlineKeyboardButton("DENY", callback_data=f"alias deny {alias.id} {user[0]}"),
            ],
            # TODO: Maybe add the report mechanic again in the future
            # [
            #     telegram.InlineKeyboardButton("DENY AND REPORT", callback_data=f"alias report {alias.id} {user[0]}"),
            # ]
        ])
    )
    client.client.shared_messages.add_message_by(
        shared_messages.ShareType.ALIAS, alias.id, message.chat_id, message.message_id
    )


@dispatcher.register_for(schemas.EventType.ALIAS_CONFIRMED)
async def _handle_alias_confirmed(event: schemas.Event):
    app_name = event.data["app"]
    alias = (await client.client.get_aliases(int(event.data["id"])))[0]
    assert alias.confirmed
    user = await client.client.get_user(int(event.data["user"]))
    assert alias.user_id == user.id

    if app_name == client.client.app_name:
        with client.client.get_new_session() as session:
            registrations = session.query(persistence.RegistrationProcess).filter_by(core_user_id=user.id).all()
            for r in registrations:
                session.delete(r)
            session.commit()

    text = (
        f"The new alias '{alias.username}' for the app '{app_name}' has been confirmed. "
        f"It is now connected to your user account. You now have a total of {len(user.aliases)} "
        f"connected aliases.\nIf this action has not been performed by you, you should disable that alias."
    )
    optional_receiver = client.client.find_telegram_user(user.id)
    try:
        if optional_receiver is not None:
            telegram_id, _ = optional_receiver
            client.client.bot.send_message(telegram_id, text)
        for shared_msg in client.client.shared_messages.get_messages(shared_messages.ShareType.ALIAS, alias.id):
            client.client.bot.delete_message(shared_msg.chat_id, shared_msg.message_id)
            client.client.shared_messages.delete_message(shared_msg)
    except:
        for shared_msg in client.client.shared_messages.get_messages(shared_messages.ShareType.ALIAS, alias.id):
            client.client.bot.edit_message_text(text, shared_msg.chat_id, shared_msg.message_id, reply_markup=None)
            client.client.shared_messages.delete_message(shared_msg)
        raise
