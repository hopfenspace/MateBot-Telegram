"""
MateBot command executor classes for /start
"""

from typing import List

import telegram

from matebot_telegram import connector, schemas, util
from matebot_telegram.base import BaseCommand, BaseCallbackQuery
from matebot_telegram.parsing.util import Namespace


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
                "It looks like you are a new user. Did you already use this bot in some other application?",
                reply_markup=telegram.InlineKeyboardMarkup([[
                    telegram.InlineKeyboardButton("YES", callback_data=f"start init {sender.id} existing"),
                    telegram.InlineKeyboardButton("NO", callback_data=f"start init {sender.id} new")
                ]])
            )

        else:
            update.message.reply_text("You are already registered. Using this command twice has no means.")

        # if MateBotUser.get_uid_from_tid(sender.id) is not None:
        #     user = MateBotUser(sender)
        #     if not external and user.external:
        #         user.external = external
        #         update.message.reply_text(
        #             "Your account was updated. You are now an internal user."
        #         )
        #     return
        #
        # user = MateBotUser(sender)
        # user.external = external
        #
        # answer = (
        #     "**Your user account was created.** You are currently marked as "
        #     f"{'external' if external else 'internal'} user without vote permissions."
        # )
        #
        # if external:
        #     answer += (
        #         "\n\nIn order to be marked as internal user, you have to "
        #         "send the `/start` command to a privileged chat once. If "
        #         "you don't have access to them, you may ask someone to invite "
        #         "you.\nAlternatively, you can ask some internal user to act as your "
        #         "voucher. To do this, the internal user needs to execute `/vouch "
        #         "<your username>`. Afterwards, you may use this bot."
        #     )
        #
        # util.safe_send(
        #     lambda: update.message.reply_markdown(answer),
        #     lambda: update.message.reply_text(answer),
        #     answer
        # )


class StartCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /start
    """

    def __init__(self):
        super().__init__("start", "^start")
        self.commands = {
            "init": self.init,
            "set-username": self.set_username
        }

    def init(self, update: telegram.Update, connect: connector.APIConnector, data: List[str]):
        sender_id = update.callback_query.message.from_user.id
        sender, selection = data
        sender = int(sender)
        if sender_id != sender:
            raise ValueError("Wrong Telegram ID")

        if selection == "new":
            update.callback_query.message.edit_text(
                "Do you want to set a username which will be used across all MateBot applications?",
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

    def set_username(self, update: telegram.Update, connect: connector.APIConnector, data: List[str]):
        sender_id = update.callback_query.message.from_user.id
        sender, selection = data
        sender = int(sender)
        if sender_id != sender:
            raise ValueError("Wrong Telegram ID")

        if selection == "yes":
            # TODO: implement asking for the username
            update.callback_query.message.edit_text(
                "Well, this isn't implemented yet, stay tuned.",
                reply_markup=telegram.InlineKeyboardMarkup([[]])
            )
            raise RuntimeError("Implementation missing")

        elif selection == "no":
            response_user = connect.post("/v1/users", json_obj={
                "external": True,
                "permission": False,
                "voucher": None,
                "name": None
            })
            if response_user.ok:
                user = schemas.User(**response_user.json())
                response_alias = connect.post("/v1/aliases", json_obj={
                    "user_id": user.id,
                    "application": connect.app_name,
                    "app_user_id": str(sender_id)
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

        else:
            raise ValueError("Unknown option")

    def run(self, update: telegram.Update, connect: connector.APIConnector) -> None:
        """
        Process or abort transaction requests based on incoming callback queries

        :param update: incoming Telegram update
        :type update: telegram.Update
        :param connect: API connector
        :type connect: matebot_telegram.connector.APIConnector
        :return: None
        """

        try:
            command, *data = self.data.split(" ")

            if command in self.commands:
                self.commands[command](update, connect, data)

            raise IndexError("Unknown command")

        except (IndexError, ValueError, TypeError, RuntimeError):
            update.callback_query.answer(
                text="There was an error processing your request!",
                show_alert=True
            )
            update.callback_query.message.edit_text(
                "There was an error processing this request. Please try again using /start.",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
            raise
