"""
MateBot inline query executors to forward collective operations
"""

import re
import datetime
from typing import List, Optional

import telegram.ext

from matebot_sdk import exceptions, schemas

from . import communism, polls, refund
from .. import client, err, shared_messages, util
from ..base import BaseInlineQuery, BaseCallbackQuery, BaseInlineResult, BaseMessage


class ForwardCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for forwarding collective operations

    The callback query data for this class has five components joined by spaces:
     - "forward" to identify this callback query type
     - "communism"|"poll"|refund" to identify the collective operation type
     - {int} as ID of the respective collective to identify it safely
     - "abort"|"ask" as the operation of the forwarding process
       - "abort" to delete the message of the bot (with origin user verification)
       - "ask" will respond with a short notice that the user has to answer this bot
         directly together with the abort button (which is also used for identification)
     - {int}|"-1" to verify the sender of the reply message to the query ("-1" if not available)
    """

    DATA_REGEX: re.Pattern = re.compile(r"^(communism|poll|refund) (\d+) (abort|ask) ((?<=abort )\d+|(?<=ask )-1)$")

    def __init__(self):
        super().__init__(
            "forward",
            "^forward",
            {"": self.handle}
        )

    async def handle(self, update: telegram.Update) -> None:
        cb = update.callback_query
        match = self.DATA_REGEX.match(self.data)
        if not match:
            self.logger.debug(f"Unknown forward callback query ignored: {self.data!r}")
            return
        collective_type, collective_id, cmd, user_id = match.groups()
        collective_id, user_id = int(collective_id), int(user_id)

        getter = {
            "communism": self.client.get_communisms,
            "poll": self.client.get_polls,
            "refund": self.client.get_refunds
        }[collective_type]
        collectives = await getter(id=collective_id, active=True)
        if len(collectives) != 1:
            return

        if cmd == "abort":
            if cb.from_user.id != user_id:
                cb.answer("You are not permitted to perform this operation.", show_alert=True)
                return
            cb.delete_message()
        elif cmd == "ask":
            cb.message.reply_text(
                f"Do you want to share this {collective_type} with somebody who doesn't have access to this chat? "
                f"Just reply to this message with the username and the {collective_type} will be forwarded privately.",
                reply_markup=telegram.InlineKeyboardMarkup([[telegram.InlineKeyboardButton(
                    f"Don't forward this {collective_type}",
                    callback_data=f"forward {collective_type} {collective_id} abort {cb.from_user.id}"
                )]])
            )


class ForwardReplyMessage(BaseMessage):
    """
    Handler for dynamic forward reply messages, i.e. users replying to forward requests with a username
    """

    DATA_REGEX: re.Pattern = re.compile(r"^forward (communism|poll|refund) (\d+) (abort) (\d+)$")

    def __init__(self):
        super().__init__("forward")

    async def run(self, msg: telegram.Message, context: telegram.ext.CallbackContext) -> None:
        if msg.reply_to_message is None:
            self.logger.error("ForwardReply doesn't have a reply_to_message, see msg below (debug)")
            self.logger.debug(str(msg))
            return
        keyboard = msg.reply_to_message.reply_markup.inline_keyboard
        if len(keyboard) != 1 or len(keyboard[0]) != 1:
            # This is not the expected message the user is replying to, since the correct message would have one button
            return
        data = str(keyboard[0][0].callback_data)
        match = self.DATA_REGEX.match(data)
        if not match:
            self.logger.warning(f"Badly formatted callback data for forward reply message handler: {data!r}")
            return
        collective_type, collective_id, _, user_id = match.groups()
        collective_id, user_id = int(collective_id), int(user_id)
        if msg.from_user.id != user_id:
            return

        # It's ensured it's the correct user and all relevant data is known, now try to get the active collective
        getter = {
            "communism": self.client.get_communisms,
            "poll": self.client.get_polls,
            "refund": self.client.get_refunds
        }[collective_type]
        collectives = await getter(id=collective_id, active=True)
        if len(collectives) != 1:
            self.logger.warning(f"{collective_type} {collective_id} wasn't found during forward reply message handling")
            msg.reply_to_message.delete()
            return
        collective = collectives[0]

        # Search for the user referenced in the user's message
        try:
            core_user = await self.client.get_core_user(msg.text)
        except (err.MateBotException, exceptions.MateBotSDKException) as exc:
            self.logger.debug(f"During handling of the forward message {msg.text!r}: {exc!r}")
            msg.reply_text(str(exc))
            return
        telegram_user = self.client.find_telegram_user(core_user.id)
        if telegram_user is None:
            self.logger.debug(f"Core user {core_user.id} doesn't use this application; declining forwarding")
            msg.reply_text(
                f"Your search for {msg.text!r} found the user {core_user.name}. However, this user "
                f"is either not registered with this MateBot frontend or hasn't set up a shared account "
                f"on multiple applications. Therefore, forwarding this {collective_type} isn't possible."
            )
            msg.reply_to_message.delete()
            return

        new_message = msg.bot.send_message(telegram_user[0], f"Forwarding a new {collective_id} to you ...")

        if collective_type == "communism":
            collective: schemas.Communism
            client.client.shared_messages.add_message_by(
                shared_messages.ShareType.COMMUNISM,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            util.update_all_shared_messages(
                msg.bot,
                shared_messages.ShareType.COMMUNISM,
                collective_id,
                await communism.get_text(client.client, collective),
                keyboard=communism.get_keyboard(collective),
                job_queue=client.client.job_queue
            )
        elif collective_type == "poll":
            collective: schemas.Poll
            client.client.shared_messages.add_message_by(
                shared_messages.ShareType.POLL,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            util.update_all_shared_messages(
                client.client.bot,
                shared_messages.ShareType.POLL,
                collective_id,
                await polls.get_text(client.client, collective),
                keyboard=polls.get_keyboard(collective),
                job_queue=client.client.job_queue
            )
        elif collective_type == "refund":
            collective: schemas.Refund
            client.client.shared_messages.add_message_by(
                shared_messages.ShareType.REFUND,
                collective_id,
                new_message.chat_id,
                new_message.message_id
            )
            util.update_all_shared_messages(
                client.client.bot,
                shared_messages.ShareType.REFUND,
                collective_id,
                await refund.get_text(None, collective),
                keyboard=refund.get_keyboard(collective),
                job_queue=client.client.job_queue
            )
        msg.reply_to_message.edit_text(f"This {collective} is forwarded to {core_user.name} ...", reply_markup=None)


class ForwardInlineQuery(BaseInlineQuery):
    """
    User selection for forwarding collective operation messages to other users

    This feature is used to allow users to select a recipient from
    all known users in the database. This recipient will get the
    forwarded collective operation message in a private chat message.
    To use this feature, the bot must be able to receive *all* updates
    for chosen inline query results. You may need to enable this
    updates via the ``@BotFather``. Set the quota to 100%.
    """

    def get_result_id(
            self,
            collective_type: Optional[str] = None,
            collective_id: Optional[int] = None,
            receiver: Optional[int] = None
    ) -> str:
        """
        Generate a result ID based on the collective type, its ID and receiving user ID

        Note that both a collective type, its ID and a receiver are necessary in
        order to generate the result ID that encodes the information to forward a
        collective. If any value is set while at least one of those parameters is
        not present, it will raise a ValueError. Note that the help query uses a
        different result ID format than the answers to the forwarding queries.

        :param collective_type: name of the collective operation type to be forwarded
        :type collective_type: typing.Optional[str]
        :param collective_id: internal ID of the collective operation to be forwarded
        :type collective_id: typing.Optional[int]
        :param receiver: Telegram ID (Chat ID) of the recipient of the forwarded message
        :type receiver: typing.Optional[int]
        :return: string encoding information to forward communisms or a random UUID
        :rtype: str
        """

        now = int(datetime.datetime.now().timestamp())
        unset_values = collective_type is None, collective_id is None, receiver is None
        if all(unset_values):
            return f"forward-help-{now}"
        if any(unset_values):
            raise ValueError("Not all required arguments set")
        return f"forward-{now}-{collective_type}-{collective_id}-{receiver}"

    def get_help(self, collective_type: Optional[str] = None) -> telegram.InlineQueryResultArticle:
        """
        Get the help option in the list of choices

        :param collective_type: name of the collective type that should be forwarded
        :type collective_type: typing.Optional[str]
        :return: inline query result choice for the help message
        :rtype: telegram.InlineQueryResultArticle
        """

        return self.get_result(
            "Help: What should I do here?",
            "*Help on using the inline mode of this bot*\n\n"
            "This bot enables users to forward communism and payment management "
            "messages to other users via a pretty comfortable inline search. "
            "Click on the button `FORWARD` of the message and then type the name, "
            "username or a part of it in the input field. There should already be "
            "a number besides the name of the bot. This number is required, forwarding "
            "does not work without this number. _Do not change it._ If you don't have "
            "a communism or payment message, you may try creating a new one. Use the "
            "commands /communism and /pay for this purpose, respectively. Use /help "
            "for a general help and an overview of other available commands."
        )

    async def _run(self, query: telegram.InlineQuery) -> List[telegram.InlineQueryResult]:
        try:
            await client.client.get_core_user(query.from_user)
        except (err.UniqueUserNotFound, err.UserNotVerified):
            return [self.get_result(
                "Service unavailable",
                "You need to create or verify your account before proceeding. See /help for more details."
            )]

        answers = []
        help_match = re.fullmatch(r"^forward (communism|poll|refund)( \d*)( \S*)?$", query.query)
        if help_match:
            help_match = help_match.group(1)
        answers.append(self.get_help(help_match))

        search_match = re.fullmatch(r"^forward (communism|poll|refund) (\d+) (\S+)$", query.query)
        if search_match:
            collective_t, collective_id, receiver = search_match.groups()
            search_function = {
                "communism": client.client.get_communisms,
                "poll": client.client.get_polls,
                "refund": client.client.get_refunds
            }[collective_t]
            search_results = await search_function(id=int(collective_id))
            if len(search_results) != 1:
                return [self.get_result(
                    f"{collective_t.title()} ID not found",
                    f"Forwarding the {collective_t} failed, because the "
                    f"{collective_t} ID was not found. Always make sure that "
                    f"the unique number in the inline query was not altered."
                )]
            collective = search_results[0]

            now = int(datetime.datetime.now().timestamp())
            try:
                core_user = await self.client.get_core_user(receiver)
            except err.MateBotException as exc:
                self.logger.debug(f"Ignoring exception {exc!r} for core user lookup {receiver!r}")
                answers.append(self.get_result(
                    f"No such user found",
                    str(exc) or "No such user found",
                    result_id=f"forward-none-{now}-0"
                ))
            else:
                if any(a for a in core_user.aliases if a.confirmed and a.application_id == client.client.app_id):
                    answers.append(self.get_result(
                        f"Forward this {collective_t} to {core_user.name}",
                        f"I am forwarding this collective to {core_user.name}...",
                        collective_t,
                        collective.id,
                        core_user.id
                    ))
                else:
                    answers.append(self.get_result(
                        f"User {core_user.name} can't be reached",
                        f"Sorry, but you can't forward this {collective_t} to {core_user.name} "
                        f"because that user either doesn't use the Telegram frontend of the "
                        f"MateBot or hasn't completely verified the linked account yet.",
                        result_id=f"forward-none-{now}-{core_user.id}"
                    ))

        # matebot_sdk.schemas

        # if len(query.query) == 0:
        #     return
        #
        # split = query.query.split(" ")
        #
        # try:
        #     collective_id = int(split[0])
        #     community = CommunityUser()
        #     try:
        #         BaseCollective.get_type(collective_id)
        #     except IndexError:
        #         query.answer([self.get_result(
        #             "Communism/payment ID not found!",
        #             "Forwarding the communism or payment request failed, because "
        #             "the communism or payment ID was not found. Always make sure "
        #             "that the unique number in the inline query was not altered."
        #         )])
        #         raise
        #
        #     users = []
        #     for word in split[1:]:
        #         if len(word) <= 1:
        #             continue
        #         if word.startswith("@"):
        #             word = word[1:]
        #
        #         for target in finders.find_names_by_pattern(word):
        #             user = finders.find_user_by_name(target)
        #             if user is not None and user not in users:
        #                 if user.uid != community.uid:
        #                     users.append(user)
        #
        #         for target in finders.find_usernames_by_pattern(word):
        #             user = finders.find_user_by_username(target)
        #             if user is not None and user not in users:
        #                 if user.uid != community.uid:
        #                     users.append(user)
        #
        #     users.sort(key=lambda u: u.name.lower())
        #
        #     answers = []
        #     for choice in users:
        #         answers.append(self.get_result(
        #             str(choice),
        #             f"I am forwarding this collective to {choice.name}...",
        #             collective_id,
        #             choice.tid
        #         ))
        #
        #     query.answer([self.get_help()] + answers)
        #
        # except (IndexError, ValueError):
        #     query.answer([self.get_help()])

        return answers

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Search for a user in the database and allow the user to forward collective operations

        :param query: inline query as part of an incoming Update
        :type query: telegram.InlineQuery
        :return: None
        """

        query.answer(util.execute_func(self._run, self.logger, query))


class ForwardInlineResult(BaseInlineResult):
    """
    Collective management message forwarding based on the inline query result reports

    This feature is used to forward collective management messages
    to other users. The receiver of the forwarded message had to be
    selected by another user using the inline query functionality.
    The ``result_id`` should store the static string ``forward``,
    the encoded UNIX timestamp, the internal collective ID and
    the receiver's Telegram ID to forward messages successfully.
    """

    def run(self, result: telegram.ChosenInlineResult, bot: telegram.Bot) -> None:
        """
        Forward a communism management message to other users

        :param result: report of the chosen inline query option as part of an incoming Update
        :type result: telegram.ChosenInlineResult
        :param bot: currently used Telegram Bot object
        :type bot: telegram.Bot
        :return: None
        """

        # No exceptions will be handled because errors here would mean
        # problems with the result ID which is generated by the bot itself
        command_name, ts, collective_id, receiver = result.result_id.split("-")
        if command_name != "forward":
            return

        # collective_id = int(collective_id)
        # receiver = MateBotUser(MateBotUser.get_uid_from_tid(int(receiver)))
        # sender = MateBotUser(result.from_user)
        #
        # type_flag = bool(BaseCollective.get_type(collective_id))
        # if type_flag:
        #     Communism(collective_id).forward(receiver, bot, sender)
        # else:
        #     Payment(collective_id).forward(receiver, bot, sender)
