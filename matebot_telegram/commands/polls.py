"""
MateBot command executor classes for /poll and its callback queries
"""

import telegram
from matebot_sdk.schemas import PollVariant
from matebot_sdk.exceptions import APIException

from .. import util
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.types import user_type
from ..parsing.util import Namespace


class PollCommand(BaseCommand):
    """
    Command executor for /poll
    """

    def __init__(self):
        super().__init__(
            "poll",
            "Use this command to manage community polls.\n\n"
            "Community polls are used to grant users new permissions or revoke them. "
            "It's a ballot where the members of the community who already have the "
            "special permission to vote on such polls determine the outcome together.\n\n"
            "There are two types of polls with granting and revoking requests. The "
            "first type is used to grant users the internal membership privilege, "
            "which is used for actions like vouching or refund actions. The second type "
            "is the request about the aforementioned voting permissions itself.\n\n"
            "Use this command to create a new poll. Optionally, specify a username "
            "when you want to create the poll about somebody else but you, i.e. if you "
            "want the community to vote whether that other user should be banished."
        )

        self.parser.add_argument("user", type=user_type, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = await self.client.get_core_user(update.effective_message.from_user)
        affected_user = args.user or sender

        def e(variant: PollVariant) -> str:
            return f"poll new {affected_user.id} {variant.value} {update.effective_message.from_user.id}"

        content = (
            f"*Poll request by {sender.name}*\n\n"
            f"Affected user: {affected_user.name}\n"
            "Which type of poll do you want to create?"
        )
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton("REQUEST INTERNAL", callback_data=e(PollVariant.GET_INTERNAL)),
            telegram.InlineKeyboardButton("REVOKE INTERNAL", callback_data=e(PollVariant.LOOSE_INTERNAL))
        ], [
            telegram.InlineKeyboardButton("REQUEST PERMISSIONS", callback_data=e(PollVariant.GET_PERMISSION)),
            telegram.InlineKeyboardButton("REVOKE PERMISSIONS", callback_data=e(PollVariant.LOOSE_PERMISSION))
        ]])

        util.safe_call(
            lambda: update.effective_message.reply_text(content, reply_markup=keyboard, parse_mode="Markdown"),
            lambda: update.effective_message.reply_text(content, reply_markup=keyboard)
        )


class PollCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /poll
    """

    def __init__(self):
        super().__init__("poll", "^poll", {
            "new": self.new,
        })

    async def new(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, affected_user, poll_type, original_sender = self.data.split(" ")
        affected_user = int(affected_user)
        original_sender = int(original_sender)
        poll_type = PollVariant(poll_type)

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer(f"Only the creator of this poll request can use it!")
            return

        issuer = await self.client.get_core_user(update.callback_query.from_user)
        try:
            poll = await self.client.create_poll(affected_user, issuer, poll_type)
        except APIException as exc:
            update.callback_query.message.edit_text(exc.message)
            return

        # TODO
        update.callback_query.message.edit_text(str(poll))
