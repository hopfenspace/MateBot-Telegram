"""
MateBot command executor classes for /start
"""

import base64

import telegram.ext

from ..client import SDK
from ..base import BaseCommand, BaseCallbackQuery, BaseMessage
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

    async def run(self, args: Namespace, update: telegram.Update) -> None:
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

        users = await SDK.get_users_by_app_alias(str(sender.id))
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
            "use-username": self.use_username,
            "select-username": self.select_username,
            "select-app": self.select_app
        })

    async def init(self, update: telegram.Update):
        _, sender, selection = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        other_apps = [app for app in await SDK.get_applications() if app.id != (await SDK.application).id]

        if selection == "new" or len(other_apps) == 0:
            update.callback_query.message.edit_text(
                "Do you want to set a username which will be used across all MateBot applications? "
                "This is highly recommended, since otherwise your numeric ID will be used as username.",
                reply_markup=telegram.InlineKeyboardMarkup([[
                    telegram.InlineKeyboardButton("YES", callback_data=f"start use-username {sender} yes"),
                    telegram.InlineKeyboardButton("NO", callback_data=f"start use-username {sender} no")
                ]])
            )

        elif selection == "existing":
            no_app = telegram.InlineKeyboardButton("None of them", callback_data=f"start select-app {sender} -1")
            update.callback_query.message.edit_text(
                "Which other application have you used before?",
                reply_markup=telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton(
                    app.name,
                    callback_data=f"start select-app {sender} {app.id}"
                )] for app in other_apps] + [[no_app]])
            )

        else:
            raise ValueError(f"Unknown option {selection!r}")

    async def use_username(self, update: telegram.Update):
        _, sender, selection = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if selection == "yes":
            def encode(s: str) -> str:
                return base64.b64encode(s.encode("UTF-8")).decode("ASCII")
            from_user = update.callback_query.from_user
            keyboard = [
                [telegram.InlineKeyboardButton(
                    name,
                    callback_data=f"start select-username {sender} {encode(name)}"
                )]
                for name in [from_user.username, from_user.first_name, from_user.full_name]
                if name is not None
            ]
            update.callback_query.message.edit_text(
                "Which username do you want to use?",
                reply_markup=telegram.InlineKeyboardMarkup(keyboard)
            )

        elif selection == "no":
            await SDK.create_new_user(str(sender), None)
            update.callback_query.message.edit_text(
                "Your account has been created. Use /help to show available commands."
            )

        else:
            raise ValueError(f"Unknown option {selection!r}")

    async def select_app(self, update: telegram.Update):
        _, sender, app_id = self.data.split(" ")
        sender = int(sender)
        app_id = int(app_id)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if app_id == -1:
            self.data = f"init {sender} new"
            await self.init(update)
            return

        raise NotImplementedError

    async def select_username(self, update: telegram.Update):
        _, sender, encoded_name = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")


class StartMessage(BaseMessage):
    def __init__(self):
        super().__init__("start")
