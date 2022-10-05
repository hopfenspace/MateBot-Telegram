"""
MateBot command executor classes for /communism and its callback queries
"""

from typing import Callable, Coroutine, Optional, Tuple

import telegram.ext
from matebot_sdk import schemas
from matebot_sdk.exceptions import APIException

from .. import client, shared_messages, util
from ..api_callback import dispatcher
from ..base import BaseCommand, BaseCallbackQuery
from ..parsing.types import amount as amount_type
from ..parsing.actions import JoinAction
from ..parsing.util import Namespace


async def _get_text(sdk: client.AsyncMateBotSDKForTelegram, communism: schemas.Communism) -> str:
    creator = await sdk.get_user(communism.id)
    usernames = ", ".join(f"{p.user_name} ({p.quantity}x)" for p in communism.participants) or "None"
    markdown = (
        f"*Communism by {creator.name}*\n\n"
        f"Reason: {communism.description}\n"
        f"Amount: {sdk.format_balance(communism.amount)}\n"
        f"Joined users ({sum(p.quantity for p in communism.participants)}): {usernames}\n"
    )

    if communism.active:
        markdown += "\n_The communism is currently active._"
    elif not communism.active:
        markdown += "\n_The communism has been closed._"
        if communism.multi_transaction:
            markdown += f"\n{len(communism.multi_transaction.transactions)} transactions have been processed "
            markdown += f"for a total value of {sdk.format_balance(communism.multi_transaction.total_amount)}. "
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
            telegram.InlineKeyboardButton("FORWARD", switch_inline_query_current_chat=f"communism {communism.id} ")
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
            "the money from each unregistered user by yourself. After everyone has joined, "
            "you close the communism to calculate and evenly distribute the price.\n\n"
            "There are two subcommands that can be used. You can get your most recent "
            "active communism as a new message in the current chat by using `show`. "
            "You can stop your most recent, currently active communism using `stop`."
        )

        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", nargs="+", action=JoinAction)

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = await self.client.get_core_user(update.effective_message.from_user)

        if args.subcommand is None:
            try:
                communism = await self.client.create_communism(user, args.amount, args.reason)
            except APIException as exc:
                update.effective_message.reply_text(exc.message)
                return

            text = await _get_text(self.client, communism)
            keyboard = _get_keyboard(communism)
            message: telegram.Message = util.safe_call(
                lambda: update.effective_message.reply_markdown(text, reply_markup=keyboard),
                lambda: update.effective_message.reply_text(text, reply_markup=keyboard),
                use_result=True
            )
            if not self.client.shared_messages.add_message_by(
                shared_messages.ShareType.COMMUNISM, communism.id, message.chat_id, message.message_id
            ):
                self.logger.error(f"Failed to add shared message for communism {communism.id}: {message.to_dict()}")

            util.send_auto_share_messages(
                update.effective_message.bot,
                shared_messages.ShareType.COMMUNISM,
                communism.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                excluded=[message.chat_id],
                job_queue=self.client.job_queue
            )
            return

        active_communisms = await self.client.get_communisms(active=True, creator_id=user.id)
        if not active_communisms:
            update.effective_message.reply_text("You don't have a communism in progress.")
            return

        if len(active_communisms) > 1:
            update.effective_message.reply_text(
                "You have more than one active communism. The command will affect the most recent active communism."
            )

        if args.subcommand == "show":
            # TODO: implement showing the currently active communism in the current chat & updating the shared messages
            update.effective_message.reply_text("Not implemented yet.")
            raise NotImplementedError

        elif args.subcommand == "stop":
            aborted_communism = await self.client.abort_communism(active_communisms[-1], user)
            text = await _get_text(self.client, aborted_communism)
            keyboard = _get_keyboard(aborted_communism)

            util.update_all_shared_messages(
                update.effective_message.bot,
                shared_messages.ShareType.COMMUNISM,
                aborted_communism.id,
                text,
                logger=self.logger,
                keyboard=keyboard,
                delete_shared_messages=True,
                job_queue=self.client.job_queue
            )

        else:
            raise RuntimeError(f"Invalid communism subcommand detected, this shouldn't happen: {args.subcommand!r}")


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

    async def _handle_communism_updates(
            self,
            update: telegram.Update,
            pre_check_func: Callable[[schemas.Communism, schemas.User], Tuple[str, bool]],
            get_sdk_func: Callable[[schemas.Communism, schemas.User], Coroutine],
            after_update_func: Optional[Callable[[schemas.Communism, schemas.User], None]] = None
    ) -> None:
        _, communism_id = self.data.split(" ")
        communism_id = int(communism_id)

        user = await SDK.get_user_by_app_alias(str(update.callback_query.from_user.id))
        communism = await SDK.get_communism_by_id(communism_id)
        pre_check = pre_check_func(communism, user)
        if pre_check[0]:
            update.callback_query.answer(text=pre_check[0], show_alert=pre_check[1])
            return

        result = await get_sdk_func(communism, user)
        if isinstance(result, schemas.Communism) and result.id == communism.id:
            communism = result

        util.update_all_shared_messages(
            update.callback_query.bot,
            "communism",
            communism.id,
            await _get_text(communism),
            self.logger,
            _get_keyboard(communism),
            telegram.ParseMode.MARKDOWN
        )

        if after_update_func:
            after_update_func(communism, user)

    async def join(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_communism_updates(
            update,
            lambda c, u: ("", False),
            lambda c, u: SDK.increase_communism_member(c, u, 1)
        )

    async def leave(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_communism_updates(
            update,
            lambda c, u: ("", False),
            lambda c, u: SDK.decrease_communism_member(c, u, 1)
        )

    async def accept(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_communism_updates(
            update,
            lambda c, u:
            ("", False)
            if c.creator_id == u.id
            else ("You can't accept this communism. You are not the creator.", True),
            lambda c, u: SDK.accept_communism(c),
            lambda c, u: shared_message_handler.delete_messages("communism", c.id)
        )

    async def cancel(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        return await self._handle_communism_updates(
            update,
            lambda c, u:
                ("", False)
                if c.creator_id == u.id
                else ("You can't close this communism. You are not the creator.", True),
            lambda c, u: SDK.cancel_communism(c),
            lambda c, u: shared_message_handler.delete_messages("communism", c.id)
        )


async def _handle_create_communism(event: schemas.Event):
    # util.send_auto_share_messages(
    #     bot, "communism", id_, await _get_text(communism), logger, _get_keyboard(communism)
    # )
    raise NotImplementedError


async def _handle_update_communism(event: schemas.Event):
    # communism = await SDK.get_communism_by_id(id_)
    # util.update_all_shared_messages(
    #     bot, "communism", id_, await _get_text(communism), logger, _get_keyboard(communism)
    # )
    raise NotImplementedError


@dispatcher.register_for(schemas.EventType.COMMUNISM_CLOSED)
async def _handle_closed_communism(event: schemas.Event):
    # communism = await SDK.get_communism_by_id(id_)
    # util.update_all_shared_messages(
    #     bot, "communism", id_, await _get_text(communism), logger, _get_keyboard(communism)
    # )
    # shared_message_handler.delete_messages("communism", communism.id)
    raise NotImplementedError


dispatcher.register(schemas.EventType.COMMUNISM_CREATED, _handle_create_communism)
dispatcher.register(schemas.EventType.COMMUNISM_UPDATED, _handle_update_communism)
# dispatcher.register(schemas.EventType.COMMUNISM_CLOSED, _handle_closed_communism)
