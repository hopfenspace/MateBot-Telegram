"""
MateBot message handler for the signup procedure (initiated by the command /start)
"""

import telegram.ext
from matebot_sdk.exceptions import MateBotSDKException

from ..base import BaseMessage, ExtendedContext
from ... import models


class StartReplyMessage(BaseMessage):
    """
    Message handler for registering new users and selecting foreign aliases or setting custom usernames
    """

    def __init__(self):
        super().__init__("start")

    async def run(self, msg: telegram.Message, context: ExtendedContext) -> None:
        sender = msg.from_user.id
        with context.application.client.get_new_session() as session:
            record = session.query(models.RegistrationProcess).get(msg.from_user.id)
            if record is None:
                # No message is expected if the user isn't currently signing up
                return

            if record.application_id != -1 and record.core_user_id is None:
                # Expecting the foreign app alias as the content of the message
                alias = msg.text
                app = record.application_id
                apps = await context.application.client.get_applications(id=app)
                if len(apps) != 1:
                    self.logger.warning(f"App {app} doesn't exist while connecting new user account")
                    await msg.reply_text(
                        "This application doesn't exist anymore. Please abort and try again.",
                        reply_markup=telegram.InlineKeyboardMarkup([[
                            telegram.InlineKeyboardButton("ABORT SIGN-UP", callback_data=f"start abort {sender}")
                        ]])
                    )
                    return

                users = await context.application.client.get_users(
                    community=False,
                    active=True,
                    alias_application_id=app,
                    alias_confirmed=True,
                    alias_username=alias
                )
                if len(users) == 1:
                    user = users[0]
                else:
                    try:
                        user = await context.application.client.get_user(alias)
                    except MateBotSDKException:
                        await msg.reply_text(
                            f"No user known as '{alias}' and no alias '{alias}' for application "
                            f"{apps[0].name!r} has been found. Please ensure that you "
                            f"spelled it correctly and try again by replying to this message.",
                            reply_markup=telegram.InlineKeyboardMarkup([[
                                telegram.InlineKeyboardButton("ABORT SIGN-UP", callback_data=f"start abort {sender}")
                            ]])
                        )
                        return

                record.core_user_id = user.id
                session.add(record)
                session.commit()

                await msg.reply_text(
                    f"An existing user '{user.name}' has been found. Do you want to continue connecting your accounts?",
                    reply_markup=telegram.InlineKeyboardMarkup([[
                        telegram.InlineKeyboardButton("YES", callback_data=f"start connect {sender}"),
                        telegram.InlineKeyboardButton("NO", callback_data=f"start abort {sender}")
                    ]])
                )
                return

            elif record.application_id == -1 and record.selected_username is None:
                # Expecting the new username as the content of the message
                username = msg.text
                if await context.application.client.get_users(name=username):
                    await msg.reply_text(
                        f"Sorry, the username '{username}' is not available. "
                        "Please choose another name by replying.",
                        reply_markup=telegram.InlineKeyboardMarkup([[
                            telegram.InlineKeyboardButton("ABORT SIGN-UP", callback_data=f"start abort {sender}")
                        ]])
                    )
                else:
                    await msg.reply_text(
                        f"Great! So, your username will be '{username}', right?",
                        reply_markup=telegram.InlineKeyboardMarkup([[
                            telegram.InlineKeyboardButton("YES", callback_data=f"start register {sender} {username}"),
                            telegram.InlineKeyboardButton("NO, ABORT", callback_data=f"start abort {sender}")
                        ]])
                    )
                return

            else:
                await msg.reply_text("Sorry, something went wrong unexpectedly! :(\nPlease file a bug report.")
                self.logger.debug(f"Record: {record.__dict__}")
                self.logger.warning(f"Invalid registration setup for user {sender}")
                raise RuntimeError("Registration record is in a bad state")
