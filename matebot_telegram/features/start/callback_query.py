"""
MateBot callback query for the start command
"""

import telegram

from ... import models
from ...base import BaseCallbackQuery, ExtendedContext


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

    async def init(self, update: telegram.Update, context: ExtendedContext, data: str):
        """
        Handle the initial question to new users ("have you used the MateBot service before?")
        """

        _, sender, selection = data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        other_apps = [
            app for app in await context.application.client.get_applications()
            if app.id != context.application.client.app_id
        ]

        if selection == "new" or len(other_apps) == 0:
            from_user = update.callback_query.from_user
            usernames = [
                e for e in {from_user.username, from_user.first_name, from_user.full_name}
                if not (await context.application.client.get_users(name=e, active=True))
            ]
            if not usernames:
                return await self.set_name(update, context, f"start set-name {sender}")

            def get_button(name: str) -> list:
                return [
                    telegram.InlineKeyboardButton(f"USE '{name}'", callback_data=f"start register {sender} {name}")
                ]

            await update.callback_query.message.edit_text(
                "Do you want to use your current username across all MateBot applications? You can "
                "alternatively sign up with a custom username, which will be used across all MateBot apps.",
                reply_markup=telegram.InlineKeyboardMarkup(
                    [get_button(name) for name in usernames]
                    + [[telegram.InlineKeyboardButton("GET A NEW NAME", callback_data=f"start set-name {sender}")]]
                )
            )

        elif selection == "existing":
            no_app = telegram.InlineKeyboardButton("None of them", callback_data=f"start select-app {sender} -1")
            await update.callback_query.message.edit_text(
                "Which other application have you used before?",
                reply_markup=telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton(
                    app.name,
                    callback_data=f"start select-app {sender} {app.id}"
                )] for app in other_apps] + [[no_app]])
            )

        else:
            raise ValueError(f"Unknown option {selection!r}")

    async def register(self, update: telegram.Update, context: ExtendedContext, data: str):
        """
        Handle the second step where a user wants to create a new user account
        """

        _, sender, *selection = data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if not selection:
            return await self.set_name(update, context, f"set-name {sender}")

        username = " ".join(selection)
        if await context.application.client.get_users(name=username):
            await update.callback_query.answer(f"Sorry, the username '{username}' is not available.", show_alert=True)
            return await self.set_name(update, context, f"set-name {sender}")

        user = await context.application.client.sign_up_new_user(update.callback_query.from_user, username)
        self.logger.info(f"Added new app user: {user.name} / {user.id} (telegram ID {sender})")
        await update.callback_query.message.edit_text(
            "Your account has been created. Use /help to show available commands."
        )
        await update.callback_query.answer()

    async def abort(self, update: telegram.Update, context: ExtendedContext, data: str):
        """
        Handle the cancellation of the registration process
        """

        _, sender = data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        self.logger.debug("Aborting registration process")
        with context.application.client.get_new_session() as session:
            record = session.query(models.RegistrationProcess).get(sender)
            if record is not None:
                session.delete(record)
                session.commit()

        await update.callback_query.message.edit_text("You have aborted the registration process. Use /start to begin.")

    async def connect(self, update: telegram.Update, context: ExtendedContext, data: str):
        """
        TODO
        """

        _, sender = data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        with context.application.client.get_new_session() as session:
            registration: models.RegistrationProcess = session.query(models.RegistrationProcess).get(sender)
            if registration is None:
                await update.callback_query.message.edit_text(
                    "This feature can't be used, use /start to begin registration."
                )
                return
            if (registration.application_id and registration.application_id == -1) or registration.core_user_id is None:
                await update.callback_query.message.edit_text(
                    "Connecting with no selected user account is not supported."
                )
                return
            user_id = registration.core_user_id

        user = await context.application.client.sign_up_as_alias(update.callback_query.from_user, user_id)
        self.logger.info(f"Added new alias for user: {user.name} / {user.id} (telegram ID {sender})")
        await update.callback_query.message.edit_text(
            "Your account has been connected. Use /help to show available commands.\n\n"
            "Note that you can't use the application at the moment, because this application alias "
            "must be confirmed by the other application. Login into the other app and use the "
            f"confirmation features to confirm the alias '{sender}' for app '{context.application.client.app_name}'."
        )

    async def set_name(self, update: telegram.Update, context: ExtendedContext, data: str):
        """
        TODO
        """

        _, sender = data.split(" ")
        sender = int(sender)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        self.logger.debug(f"Updating start procedure for {sender} to state set_name")
        with context.application.client.get_new_session() as session:
            record = session.query(models.RegistrationProcess).get(sender)
            if record is not None:
                record.application_id = -1
            else:
                record = models.RegistrationProcess(telegram_id=sender, application_id=-1)
            session.add(record)
            session.commit()

            await update.callback_query.message.edit_text(
                "Which username to you want to use for your account? Please reply directly to this message.",
                reply_markup=telegram.InlineKeyboardMarkup([[
                    telegram.InlineKeyboardButton("ABORT SIGN-UP", callback_data=f"start abort {sender}")
                ]])
            )

    async def select_app(self, update: telegram.Update, context: ExtendedContext, data: str):
        """
        Handle the second step of the process where a user said that the MateBot service has been used before
        """

        _, sender, app_id = data.split(" ")
        sender = int(sender)
        app_id = int(app_id)
        if update.callback_query.from_user.id != sender:
            raise ValueError("Wrong Telegram ID")

        if app_id == -1:
            return await self.init(update, context, f"init {sender} new")

        apps = await context.application.client.get_applications(id=app_id)
        if not apps or len(apps) != 1 or apps[0].name == context.application.client.app_name:
            raise ValueError("Expected to find one app but this app")

        with context.application.client.get_new_session() as session:
            record = session.query(models.RegistrationProcess).get(sender)
            if record is not None:
                record.application_id = app_id
            else:
                record = models.RegistrationProcess(telegram_id=sender, application_id=app_id)
            session.add(record)
            session.commit()

        await update.callback_query.message.edit_text(
            "What's the username you have used across the MateBot instances? "
            "It's required to connect your new account with the existing one. "
            "Please reply to this message directly.",
            reply_markup=telegram.InlineKeyboardMarkup([[
                telegram.InlineKeyboardButton("ABORT SIGN-UP", callback_data=f"start abort {sender}")
            ]])
        )
