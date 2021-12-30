"""
MateBot command executor classes for /start
"""

import base64
from typing import Optional

import telegram

from .. import connector, schemas, util
from ..base import BaseCommand, BaseCallbackQuery
from ..parsing.util import Namespace


class StartCommand(BaseCommand):
    """
    Command executor for /start
    """

    def __init__(self):
        super().__init__(
            "start",
            "Use this command once per user to start interacting with this bot.\n\n"
            "This command creates your user account in case it was not yet. Otherwise, "
            "this command might not be pretty useful. Note that you should not delete "
            "the chat with the bot in order to receive personal notifications from it.\n\n"
            "Use /help for more information about how to use this bot and its commands."
        )

    def run(self, args: Namespace, update: telegram.Update, connect: connector.APIConnector) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        if update.message is None:
            return

        sender = update.message.from_user
        if sender.is_bot:
            return

        if update.message.chat.type != "private":
            update.message.reply_text("This command should be executed in private chat.")
            return

        user = util.get_user_by(update.effective_message.from_user, lambda _: None, connect)
        if user is None:
            update.message.reply_text(
                "It looks like you are a new user. Did you already use the MateBot in some other application?",
                reply_markup=telegram.InlineKeyboardMarkup([[
                    telegram.InlineKeyboardButton("YES", callback_data=f"start init {sender.id} existing"),
                    telegram.InlineKeyboardButton("NO", callback_data=f"start init {sender.id} new")
                ]])
            )

        else:
            update.message.reply_text("You are already registered. Using this command twice has no means.")


class StartCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /start
    """

    def __init__(self):
        super().__init__("start", "^start", {
            "init": self.init,
            "set-username": self.set_username,
            "select": self.select
        })

    def init(self, update: telegram.Update, connect: connector.APIConnector):
        sender_id = update.callback_query.from_user.id
        _, sender, selection = self.data.split(" ")
        sender = int(sender)
        if sender_id != sender:
            raise ValueError("Wrong Telegram ID")

        if selection == "new":
            update.callback_query.message.edit_text(
                "Do you want to set a username which will be used across all MateBot applications? "
                "This is highly recommended, since otherwise your numeric ID will be used as username.",
                reply_markup=telegram.InlineKeyboardMarkup([[
                    telegram.InlineKeyboardButton("YES", callback_data=f"start set-username {sender_id} yes"),
                    telegram.InlineKeyboardButton("NO", callback_data=f"start set-username {sender_id} no")
                ]])
            )

        elif selection == "existing":
            # TODO: implement asking for the identifier of another client alias
            update.callback_query.message.edit_text(
                "Well, this isn't implemented yet, stay tuned.",
                reply_markup=telegram.InlineKeyboardMarkup([[]])
            )
            raise RuntimeError("Implementation missing")

        else:
            raise ValueError("Unknown option")

    def set_username(self, update: telegram.Update, connect: connector.APIConnector):
        sender_id = update.callback_query.from_user.id
        _, sender, selection = self.data.split(" ")
        sender = int(sender)
        if sender_id != sender:
            raise ValueError("Wrong Telegram ID")

        if selection == "yes":
            keyboard = [
                [telegram.InlineKeyboardButton(
                    name,
                    callback_data=f"start select {sender_id} {encoded_name}"
                )]
                for name, encoded_name in [
                    (
                        update.callback_query.from_user.username,
                        base64.b64encode(update.callback_query.from_user.username.encode("UTF-8")).decode("ASCII")
                    ),
                    (
                        update.callback_query.from_user.first_name,
                        base64.b64encode(update.callback_query.from_user.first_name.encode("UTF-8")).decode("ASCII")
                    ),
                    (
                        update.callback_query.from_user.full_name,
                        base64.b64encode(update.callback_query.from_user.full_name.encode("UTF-8")).decode("ASCII")
                    )
                ]
            ]
            update.callback_query.message.edit_text(
                "Which username do you want to use?",
                reply_markup=telegram.InlineKeyboardMarkup(keyboard)
            )

        elif selection == "no":
            _create_user(update, connect, sender_id, None)

        else:
            raise ValueError("Unknown option")

    def select(self, update: telegram.Update, connect: connector.APIConnector):
        sender_id = update.callback_query.from_user.id
        _, sender, encoded_name = self.data.split(" ")
        sender = int(sender)
        if sender_id != sender:
            raise ValueError("Wrong Telegram ID")

        selected_username = base64.b64decode(encoded_name.encode("ASCII")).decode("UTF-8")
        _create_user(update, connect, sender_id, selected_username)


def _create_user(update: telegram.Update, connect: connector.APIConnector, telegram_id: int, username: Optional[str]):
    response_user = connect.post("/v1/users", json_obj={
        "external": True,
        "permission": False,
        "voucher": None,
        "name": username
    })
    if response_user.ok:
        user = schemas.User(**response_user.json())
        response_alias = connect.post("/v1/aliases", json_obj={
            "user_id": user.id,
            "application": connect.app_name,
            "app_user_id": str(telegram_id)
        })

        if response_alias.ok:
            update.callback_query.message.edit_text(
                "Your account has been successfully created.",
                reply_markup=telegram.InlineKeyboardMarkup([[]])
            )
        else:
            update.callback_query.message.edit_text(
                "Creating your account failed. Please file a bug report.",
                reply_markup=telegram.InlineKeyboardMarkup([[]])
            )
            raise RuntimeError(f"{response_alias.status_code} {response_alias.content}")

    else:
        update.callback_query.message.edit_text(
            "Creating your account failed. Please file a bug report.",
            reply_markup=telegram.InlineKeyboardMarkup([[]])
        )
        raise RuntimeError(f"{response_user.status_code} {response_user.content}")
