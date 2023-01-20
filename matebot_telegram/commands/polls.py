"""
MateBot command executor classes for /poll and its callback queries
"""

import time
import telegram
from typing import Awaitable, Callable, Optional

from matebot_sdk import exceptions, schemas

from . import _common
from .. import client, shared_messages, util
from ..api_callback import dispatcher
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.types import any_user_type
from ..parsing.util import Namespace


async def get_text(sdk: client.AsyncMateBotSDKForTelegram, poll: schemas.Poll) -> str:
    creator = await sdk.get_user(poll.creator_id)
    approving = [vote.user_name for vote in poll.votes if vote.vote]
    disapproving = [vote.user_name for vote in poll.votes if not vote.vote]

    question = {
        schemas.PollVariant.GET_INTERNAL: "join the internal group and gain its privileges",
        schemas.PollVariant.GET_PERMISSION: "get extended permissions to vote on polls",
        schemas.PollVariant.LOOSE_INTERNAL: "loose the internal privileges and be degraded to an external user",
        schemas.PollVariant.LOOSE_PERMISSION: "loose the extended permissions to vote on polls"
    }[poll.variant]
    content = (
        f"*Poll by {creator.name}*\n"
        f"Question: _Should {poll.user.name} {question}?_\n"
        f"Created: {time.asctime(time.gmtime(float(poll.created)))}\n\n"
        f"*Votes ({len(poll.votes)})*\n"
        f"Proponents ({len(approving)}): {', '.join(approving) or 'None'}\n"
        f"Opponents ({len(disapproving)}): {', '.join(disapproving) or 'None'}\n"
    )

    if poll.active:
        content += "\n_The poll is currently active._"
    else:
        if poll.accepted is not None:
            content += f"\n_The poll has been closed. The request has been {('rejected', 'accepted')[poll.accepted]}._"
        else:
            content += f"\n_The poll has been aborted._"
    return content


def get_keyboard(poll: schemas.Poll) -> telegram.InlineKeyboardMarkup:
    if not poll.active:
        return telegram.InlineKeyboardMarkup([])
    return _common.get_voting_keyboard_for("poll", poll.id)


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

        self.parser.add_argument("user", type=any_user_type, nargs="?")

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

        util.safe_call(
            lambda: update.effective_message.reply_text(content, reply_markup=keyboard, parse_mode="Markdown"),
            lambda: update.effective_message.reply_text(content, reply_markup=keyboard)
        )


class PollCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /poll
    """

    def __init__(self):
        super().__init__(
            "poll",
            "^poll",
            {
                "dont-open": self.dont_open,
                "new": self.new,
                "approve": self.approve,
                "disapprove": self.approve,
                "abort": self.abort
            }
        )

    async def dont_open(self, update: telegram.Update) -> None:
        _, _, _, original_sender = self.data.split(" ")
        if update.callback_query.from_user.id != int(original_sender):
            update.callback_query.answer("Only the creator of this poll request can use it!")
            return
        update.callback_query.message.edit_text("You chose not to open a poll right now.", reply_markup=None)
        update.callback_query.answer("No poll has been opened")

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
        poll_type = schemas.PollVariant(poll_type)

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer("Only the creator of this poll request can alter it!")
            return

        user = (await self.client.get_users(affected_user))[0]
        issuer = await self.client.get_core_user(update.callback_query.from_user)
        await _common.new_group_operation(
            self.client.create_poll(affected_user, issuer, poll_type),
            self.client,
            lambda p: get_text(self.client, p),
            get_keyboard,
            update.callback_query.message,
            shared_messages.ShareType.POLL,
            self.logger
        )
        update.callback_query.message.edit_text(
            f"You have selected the poll type for the new poll about the user {user.name}.",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )

    async def _handle_vote(
            self,
            update: telegram.Update,
            get_client_func: Callable[[int, schemas.User], Awaitable[schemas.PollVoteResponse]]
    ) -> None:
        poll_id = int(self.data.split(" ")[-1])

        user = await self.client.get_core_user(update.callback_query.from_user)
        response = await get_client_func(poll_id, user)
        update.callback_query.answer(f"You successfully voted {('against', 'for')[response.vote.vote]} the request.")

        text = await get_text(self.client, response.poll)
        keyboard = get_keyboard(response.poll)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.POLL,
            poll_id,
            text,
            logger=self.logger,
            keyboard=keyboard
        )

    async def approve(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_vote(update, self.client.approve_poll)

    async def disapprove(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_vote(update, self.client.disapprove_poll)

    async def abort(self, update: telegram.Update) -> None:
        """
        Create a new poll

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, poll_id = self.data.split(" ")
        poll_id = int(poll_id)

        issuer = await self.client.get_core_user(update.callback_query.from_user)
        try:
            poll = await self.client.abort_poll(poll_id, issuer)
        except exceptions.APIException as exc:
            update.callback_query.answer(exc.message, show_alert=True)
            return

        text = await get_text(self.client, poll)
        keyboard = get_keyboard(poll)
        util.update_all_shared_messages(
            update.callback_query.bot,
            shared_messages.ShareType.POLL,
            poll.id,
            text,
            logger=self.logger,
            keyboard=keyboard,
            delete_shared_messages=True,
            job_queue=self.client.job_queue
        )
        update.callback_query.answer()


@dispatcher.register_for(schemas.EventType.POLL_CREATED)
async def _handle_poll_created(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await client.client.get_polls(id=poll_id))[0]
    util.send_auto_share_messages(
        client.client.bot,
        shared_messages.ShareType.POLL,
        poll_id,
        await get_text(client.client, poll),
        keyboard=get_keyboard(poll),
        job_queue=client.client.job_queue
    )


@dispatcher.register_for(schemas.EventType.POLL_UPDATED)
async def _handle_poll_updated(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await client.client.get_polls(id=poll_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.POLL,
        poll_id,
        await get_text(client.client, poll),
        keyboard=get_keyboard(poll),
        job_queue=client.client.job_queue
    )


@dispatcher.register_for(schemas.EventType.POLL_CLOSED)
async def _handle_poll_closed(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await client.client.get_polls(id=poll_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.POLL,
        poll_id,
        await get_text(client.client, poll),
        keyboard=get_keyboard(poll),
        delete_shared_messages=True,
        job_queue=client.client.job_queue
    )
