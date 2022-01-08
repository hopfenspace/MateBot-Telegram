"""
MateBot command executor classes for /communism and its callback queries
"""

import typing

import telegram.ext
from matebot_sdk import schemas
from matebot_sdk.base import PermissionLevel

from .. import util
from ..base import BaseCommand, BaseCallbackQuery
from ..client import SDK
from ..parsing.types import amount as amount_type
from ..parsing.actions import JoinAction
from ..parsing.util import Namespace
from ..shared_messages import shared_message_handler


def _get_text(communism: schemas.Communism) -> str:
    users = util.get_event_loop().run_until_complete(SDK.get_users())
    creator = [user for user in users if user.id == communism.creator_id][0]

    def f(user_id: int, quantity: int) -> str:
        user = [u for u in users if u.id == user_id]
        if len(user) != 1:
            raise ValueError(f"User ID {user_id} couldn't be converted to username properly.")
        return f"{SDK.get_username(user)} ({quantity}x)"

    usernames = ', '.join(f(p.user_id, p.quantity) for p in communism.participants) or "None"
    markdown = (
        f"*Communism by {SDK.get_username(creator)}*\n\n"
        f"Reason: {communism.description}\n"
        f"Amount: {communism.amount / 100 :.2f}€\n"
        f"Joined users ({sum(p.quantity for p in communism.participants)}): {usernames}\n"
    )

    if communism.active:
        markdown += "\n_The communism is currently active._"
    elif not communism.active:
        markdown += "\n_The communism has been closed._"
        if communism.transactions:
            markdown += f"\n{len(communism.transactions)} transactions have been processed. "
            markdown += "Take a look at /history for more details."
        else:
            markdown += "\nThe communism was aborted. No transactions have been processed."

    return markdown


def _get_keyboard(communism: schemas.Communism) -> telegram.InlineKeyboardMarkup:
    if not communism.active:
        return telegram.InlineKeyboardMarkup([])

    def f(cmd):
        return f"communism {cmd} {communism.id}"

    return telegram.InlineKeyboardMarkup([
        [
            telegram.InlineKeyboardButton("JOIN (+)", callback_data=f("join")),
            telegram.InlineKeyboardButton("LEAVE (-)", callback_data=f("leave")),
        ],
        [
            telegram.InlineKeyboardButton("FORWARD", switch_inline_query_current_chat=f"{communism.id} ")
        ],
        [
            telegram.InlineKeyboardButton("ACCEPT", callback_data=f("accept")),
            telegram.InlineKeyboardButton("CANCEL", callback_data=f("cancel")),
        ]
    ])


class CommunismCommand(BaseCommand):
    """
    Command executor for /communism

    Note that the majority of the functionality is located in the query handler.
    """

    def __init__(self):
        super().__init__(
            "communism",
            "Use this command to start, stop or show a communism.\n\n"
            "When you pay for something that is used or otherwise consumed by a bigger "
            "group of people, you can open a communism for it to get your money back.\n\n"
            "When you use this command, you specify a reason and the price. The others "
            "can join afterwards (you might need to remember them). People who don't use "
            "the MateBot may be respected by joining multiple times - therefore paying more "
            "than normal and effectively taking the bill of those people. You may collect "
            "the money from each external user by yourself. After everyone has joined, "
            "you close the communism to calculate and evenly distribute the price.\n\n"
            "There are two subcommands that can be used. You can get your "
            "active communism as a new message in the current chat by using `show`. "
            "You can stop your currently active communism using `stop`."
        )

        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", nargs="+", action=JoinAction)

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = util.get_event_loop().run_until_complete(
            SDK.get_user_by_app_alias(str(update.effective_message.from_user.id))
        )
        permission_check = SDK.ensure_permissions(user, PermissionLevel.ANY_WITH_VOUCHER, "communism")
        if not permission_check[0]:
            update.effective_message.reply_text(permission_check[1])
            return

        active_communisms = util.get_event_loop().run_until_complete(SDK.get_communisms_by_creator(user))
        if args.subcommand is None:
            if active_communisms:
                update.effective_message.reply_text("You already have a communism in progress. Please handle it first.")
                return

            communism = util.get_event_loop().run_until_complete(SDK.make_new_communism(user, args.amount, args.reason))
            text = _get_text(communism)
            keyboard = _get_keyboard(communism)
            message: telegram.Message = util.safe_call(
                lambda: update.effective_message.reply_markdown(text, reply_markup=keyboard),
                lambda: update.effective_message.reply_text(text, reply_markup=keyboard),
                use_result=True
            )
            shared_message_handler.add_message_by("communism", communism.id, message.chat_id, message.message_id)
            util.send_auto_share_messages(
                update.effective_message.bot,
                "communism",
                communism.id,
                text,
                logger=self.logger,
                keyboard=keyboard
            )
            return

        if not active_communisms:
            update.effective_message.reply_text("You don't have a communism in progress.")
            return

        if len(active_communisms) > 1:
            update.effective_message.reply_text(
                "You have more than one active communism. The subcommand will use the oldest active communism."
            )

        if args.subcommand == "show":
            # TODO: implement showing the currently active communism in the current chat & updating the shared messages
            update.effective_message.reply_text("Not implemented.")

        elif args.subcommand == "stop":
            communism = util.get_event_loop().run_until_complete(SDK.cancel_communism(active_communisms[0]))
            text = _get_text(communism)
            keyboard = _get_keyboard(communism)
            util.update_all_shared_messages(
                update.effective_message.bot,
                "communism",
                communism.id,
                text,
                logger=self.logger,
                keyboard=keyboard
            )
            shared_message_handler.delete_messages("communism", communism.id)


class CommunismCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /communism
    """

    def __init__(self):
        super().__init__(
            "communism",
            "^communism",
            {
                "join": self.join,
                "leave": self.leave,
                "accept": self.accept,
                "cancel": self.cancel
            }
        )

    def _get_communism(self) -> schemas.Communism:
        """
        Retrieve the Communism object based on the callback data

        :return: Communism object that handles the current collective
        :rtype: Communism
        :raises err.CallbackError: when something went wrong
        """

        if self.data is None or self.data == "":
            raise err.CallbackError("Empty stripped callback data")

        communism_id = self.data.split(" ")[-1]
        try:
            communism_id = int(communism_id)
        except ValueError as exc:
            raise err.CallbackError("Wrong communism ID format", exc)

        try:
            return Communism(communism_id)
        except IndexError as exc:
            raise err.CallbackError("The collective does not exist in the database", exc)
        except (TypeError, RuntimeError) as exc:
            raise err.CallbackError("The collective has the wrong remote type", exc)

    def get_communism(self, query: telegram.CallbackQuery) -> typing.Optional[schemas.Communism]:
        """
        Retrieve the Communism object based on the callback data

        By convention, everything after the last space symbol
        should be interpreted as communism ID. If some error occurs
        while trying to get the Communism object, an alert message
        will be shown to the user and an exception will be raised.

        :param query: incoming Telegram callback query with its attached data
        :type query: telegram.CallbackQuery
        :return: Communism object that handles the current collective
        :rtype: typing.Optional[Communism]
        :raises err.CallbackError: when something went wrong
        """

        try:
            com = self._get_communism()
            if com.active:
                return com
            query.answer("The communism is not active anymore!")

        except err.CallbackError:
            query.answer(
                text="Your requested action was not performed! Please try again later.",
                show_alert=True
            )
            raise

    def toggle(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            user = MateBotUser(update.callback_query.from_user)
            previous_member = com.is_participating(user)[0]
            com.toggle_user(user)
            com.edit_all_messages(
                com.get_markdown(),
                com._get_inline_keyboard(),
                update.effective_message.bot
            )

            if previous_member:
                update.callback_query.answer("Okay, you were removed.")
            else:
                update.callback_query.answer("Okay, you were added.")

    def increase(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't increase the external counter. You are not the creator.",
                    show_alert=True
                )
                return

            com.externals += 1
            com.edit_all_messages(
                com.get_markdown(),
                com._get_inline_keyboard(),
                update.effective_message.bot
            )
            update.callback_query.answer("Okay, incremented.")

    def decrease(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't decrease the external counter. You are not the creator.",
                    show_alert=True
                )
                return

            if com.externals == 0:
                update.callback_query.answer(
                    text="The externals counter can't be negative!",
                    show_alert=True
                )
                return

            com.externals -= 1
            com.edit_all_messages(
                com.get_markdown(),
                com._get_inline_keyboard(),
                update.effective_message.bot
            )
            update.callback_query.answer("Okay, decremented.")

    def join(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        raise ValueError("Not implemented")

    def leave(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        raise ValueError("Not implemented")

    def accept(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't accept this communism. You are not the creator.",
                    show_alert=True
                )
                return

            if com.accept(update.callback_query.message.bot):
                update.callback_query.answer(text="The communism has been closed successfully.")
            else:
                update.callback_query.answer(
                    text="The communism was not accepted. Are there any members?",
                    show_alert=True
                )

    def cancel(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't close this communism. You are not the creator.",
                    show_alert=True
                )
                return

            if com.cancel(update.callback_query.message.bot):
                update.callback_query.answer(text="Okay, the communism was cancelled.")
