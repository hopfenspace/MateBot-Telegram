"""
MateBot command executor classes for /start
"""

import base64

import telegram

from .. import util
from ..base import BaseCommand, BaseCallbackQuery
from ..client import SDK
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

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = update.effective_message.from_user
        if sender.is_bot:
            return

        if update.message.chat.type != "private":
            update.message.reply_text("This command should be executed in private chat.")
            return

        users = util.get_event_loop().run_until_complete(SDK.get_users_by_app_alias(str(sender.id)))
        if len(users) > 0:
            update.message.reply_text("You are already registered. Using this command twice has no means.")
            return

        update.message.reply_text(
            "It looks like you are a new user. Did you already use the MateBot in some other application?",
            reply_markup=telegram.InlineKeyboardMarkup([[
                telegram.InlineKeyboardButton("YES", callback_data=f"start init {sender.id} existing"),
                telegram.InlineKeyboardButton("NO", callback_data=f"start init {sender.id} new")
            ]])
        )


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

    def init(self, update: telegram.Update):
        _, sender, selection = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if selection == "new":
            update.callback_query.message.edit_text(
                "Do you want to set a username which will be used across all MateBot applications? "
                "This is highly recommended, since otherwise your numeric ID will be used as username.",
                reply_markup=telegram.InlineKeyboardMarkup([[
                    telegram.InlineKeyboardButton("YES", callback_data=f"start set-username {sender} yes"),
                    telegram.InlineKeyboardButton("NO", callback_data=f"start set-username {sender} no")
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
            raise ValueError(f"Unknown option {selection!r}")

    def set_username(self, update: telegram.Update):
        # user = util.get_event_loop().run_until_complete(SDK.get_user_by_app_alias(str(sender)))
        _, sender, selection = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if selection == "yes":
            keyboard = [
                [telegram.InlineKeyboardButton(
                    name,
                    callback_data=f"start select {sender} {encoded_name}"
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
            util.get_event_loop().run_until_complete(SDK.create_new_user(str(sender), None))
            update.callback_query.message.edit_text(
                "Your account has been created. Use /help to show available commands."
            )

        else:
            raise ValueError(f"Unknown option {selection!r}")

    def select(self, update: telegram.Update):
        _, sender, encoded_name = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        selected_username = base64.b64decode(encoded_name.encode("ASCII")).decode("UTF-8")
        util.get_event_loop().run_until_complete(SDK.create_new_user(str(sender), selected_username))
        update.callback_query.message.edit_text("Your account has been created. Use /help to show available commands.")
