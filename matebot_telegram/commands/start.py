"""
MateBot command executor classes for /start
"""

import telegram.ext

from .. import err, persistence
from ..base import BaseCommand, BaseCallbackQuery
from ..parsing.util import Namespace


class StartCommand(BaseCommand):
    """
    Command executor for /start
    """

    def __init__(self):
        super().__init__(
            "start",
            "Start interacting with this bot, once per user\n\n"
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

        if update.message.chat.type != telegram.Chat.PRIVATE:
            update.message.reply_text("This command should be executed in private chat.")
            return

        try:
            await self.client.get_core_user(sender)
            update.message.reply_text("You are already registered. Using this command twice has no means.")
            return
        except err.UniqueUserNotFound:
            pass
        except err.MateBotException as exc:
            update.message.reply_text(str(exc))
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
            "register": self.register,
            "abort": self.abort,
            "connect": self.connect,
            "set-name": self.set_name,
            "select-app": self.select_app
        })

    async def init(self, update: telegram.Update):
        _, sender, selection = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        other_apps = [app for app in await self.client.get_applications() if app.name != self.client.app_name]

        if selection == "new" or len(other_apps) == 0:
            from_user = update.callback_query.from_user
            usernames = [
                e for e in {from_user.username, from_user.first_name, from_user.full_name}
                if not (await self.client.get_users(name=e, active=True))
            ]
            if not usernames:
                self.data = f"start set-name {sender}"
                await self.set_name(update)
                return

            def get_button(name: str) -> list:
                return [
                    telegram.InlineKeyboardButton(f"USE '{name}'", callback_data=f"start register {sender} {name}")
                ]

            update.callback_query.message.edit_text(
                "Do you want to use your current username across all MateBot applications? You can "
                "alternatively sign up with a custom username, which will be used across all MateBot apps.",
                reply_markup=telegram.InlineKeyboardMarkup(
                    [get_button(name) for name in usernames]
                    + [[telegram.InlineKeyboardButton("GET A NEW NAME", callback_data=f"start set-name {sender}")]]
                )
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

    async def register(self, update: telegram.Update):
        _, sender, *selection = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if not selection:
            self.data = f"set-name {sender}"
            return await self.set_name(update)

        username = " ".join(selection)
        if await self.client.get_users(name=username):
            update.callback_query.answer(f"Sorry, the username '{username}' is not available.", show_alert=True)
            self.data = f"set-name {sender}"
            return await self.set_name(update)

        user = await self.client.sign_up_new_user(update.callback_query.from_user, username)
        self.logger.info(f"Added new app user: {user.name} / {user.id} (telegram ID {sender})")
        update.callback_query.message.edit_text("Your account has been created. Use /help to show available commands.")

    async def abort(self, update: telegram.Update):
        _, sender = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        with self.client.get_new_session() as session:
            record = session.query(persistence.RegistrationProcess).get(sender)
            if record is not None:
                session.delete(record)
                session.commit()

        update.callback_query.message.edit_text("You have aborted the registration process. Use /start to begin.")

    async def connect(self, update: telegram.Update):
        _, sender = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        with self.client.get_new_session() as session:
            registration: persistence.RegistrationProcess = session.query(persistence.RegistrationProcess).get(sender)
            if registration is None:
                update.callback_query.message.edit_text("This feature can't be used, use /start to begin registration.")
                return
            if (registration.application_id and registration.application_id == -1) or registration.core_user_id is None:
                update.callback_query.message.edit_text("Connecting with no selected user account is not supported.")
                return
            user_id = registration.core_user_id

        user = await self.client.sign_up_as_alias(update.callback_query.from_user, user_id)
        self.logger.info(f"Added new alias for user: {user.name} / {user.id} (telegram ID {sender})")
        update.callback_query.message.edit_text(
            "Your account has been connected. Use /help to show available commands.\n\n"
            "Note that you can't use the application at the moment, because this application alias "
            "must be confirmed by the other application. Login into the other app and use the "
            f"confirmation features to confirm the alias '{sender}' for app '{self.client.app_name}'."
        )

    async def set_name(self, update: telegram.Update):
        _, sender = self.data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        with self.client.get_new_session() as session:
            record = session.query(persistence.RegistrationProcess).get(sender)
            if record is not None:
                record.application_id = -1
            else:
                record = persistence.RegistrationProcess(telegram_id=sender, application_id=-1)
            session.add(record)
            session.commit()

            update.callback_query.message.edit_text(
                "Which username to you want to use for your account? Please reply directly to this message."
            )

    async def select_app(self, update: telegram.Update):
        _, sender, app_id = self.data.split(" ")
        sender = int(sender)
        app_id = int(app_id)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if app_id == -1:
            self.data = f"init {sender} new"
            return await self.init(update)

        apps = await self.client.get_applications(id=app_id)
        if not apps or len(apps) != 1 or apps[0].name == self.client.app_name:
            raise ValueError("Expected to find one app but this app")

        with self.client.get_new_session() as session:
            record = session.query(persistence.RegistrationProcess).get(sender)
            if record is not None:
                record.application_id = app_id
            else:
                record = persistence.RegistrationProcess(telegram_id=sender, application_id=app_id)
            session.add(record)
            session.commit()

        update.callback_query.message.edit_text(
            "What's the username you have used across the MateBot instances? "
            "It's required to connect your new account with the existing one. "
            "Please reply to this message directly."
        )
