"""
MateBot command executor class for /poll
"""

import telegram
from typing import Optional

from matebot_sdk import schemas

from ..base import BaseCommand, ExtendedContext, Namespace, types


class PollCommand(BaseCommand):
    """
    Command executor for /poll
    """

    def __init__(self):
        super().__init__(
            "poll",
            "Manage community membership polls\n\n"
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

        self.parser.add_argument("user", type=types.any_user_type, nargs="?")

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        Create a new message with inline keyboard to request the type of poll
        """

        sender = await context.application.client.get_core_user(update.effective_message.from_user)
        affected_user = args.user or sender

        def f(variant: Optional[schemas.PollVariant]) -> str:
            if variant is None:
                return f"poll dont-open {affected_user.id} - {update.effective_message.from_user.id}"
            return f"poll new {affected_user.id} {variant.value} {update.effective_message.from_user.id}"

        content = (
            f"*Poll request by {sender.name}*\n\n"
            f"Affected user: {affected_user.name}\n"
            "Which type of poll do you want to create?"
        )
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton("REQUEST INTERNAL", callback_data=f(schemas.PollVariant.GET_INTERNAL)),
            telegram.InlineKeyboardButton("REVOKE INTERNAL", callback_data=f(schemas.PollVariant.LOOSE_INTERNAL))
        ], [
            telegram.InlineKeyboardButton("REQUEST PERMISSIONS", callback_data=f(schemas.PollVariant.GET_PERMISSION)),
            telegram.InlineKeyboardButton("REVOKE PERMISSIONS", callback_data=f(schemas.PollVariant.LOOSE_PERMISSION))
        ], [
            telegram.InlineKeyboardButton("Don't open a poll now", callback_data=f(None))
        ]])

        await update.effective_message.reply_markdown(content, reply_markup=keyboard)
