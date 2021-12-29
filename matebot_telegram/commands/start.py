"""
MateBot command executor classes for /start
"""

import telegram

from matebot_telegram import connector, util
from matebot_telegram.base import BaseCommand
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
            # unknown user
            update.message.reply_text(
                "It looks like you are a new user. Did you already use this bot in some other application?",
                reply_markup=telegram.InlineKeyboardMarkup([
                    [
                        telegram.InlineKeyboardButton("YES", callback_data=f"start init {sender.id} existing"),
                        telegram.InlineKeyboardButton("NO", callback_data=f"start init {sender.id} new")
                    ]
                ])
            )
            pass
        else:
            update.message.reply_text("You are already registered. Using this command twice has no means.")
            # existing user
            pass

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




