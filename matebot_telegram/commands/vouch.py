"""
MateBot command executor classes for /vouch and its callback queries
"""

from typing import Awaitable, Callable

import telegram
from matebot_sdk import exceptions, schemas

from .. import api_callback, client, util
from ..base import BaseCommand, BaseCallbackQuery
from ..parsing.types import any_user_type
from ..parsing.util import Namespace


class VouchCommand(BaseCommand):
    """
    Command executor for /vouch
    """

    def __init__(self):
        super().__init__(
            "vouch",
            "Use this command to vouch for other users.\n\n"
            "The possible interactions with this bot are pretty limited for external "
            "people for security purposes. If you intend to use this bot, you can ask an "
            "internal user to vouch for you. Doing so gives you the necessary permissions.\n\n"
            "On the other hand, internal users can vouch for externals to allow them to use "
            "this bot. You should note that you will be held responsible in case the user "
            "you are vouching for can't pay possible debts for whatever reason. If the "
            "community decides to disable the external user's account, you have to pay "
            "remaining debts, if there are any. However, you would also get the balance in "
            "case it's positive. After all, you are responsible to deal with the external user."
        )

        p = self.parser.new_usage()
        p.add_argument("command", choices=("add", "vouch", "remove", "stop"), type=lambda x: str(x).lower())
        p.add_argument("user", type=any_user_type)

    async def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender_id = update.effective_message.from_user.id
        sender = await self.client.get_core_user(update.effective_message.from_user)

        if args.command is None:
            if sender.voucher_id is not None:
                assert sender.external
                voucher = await self.client.get_user(sender.voucher_id)
                update.effective_message.reply_text(
                    "You're an external user, but you are allowed to interact "
                    f"with the bot, since {voucher.name} vouches for you."
                )
            elif sender.external:
                update.effective_message.reply_text("You need a voucher to use this and some other bot features.")
            else:
                debtors = await self.client.get_users(voucher_id=sender.id)
                if not debtors:
                    update.effective_message.reply_markdown(
                        "You currently don't vouch for anybody. Use the subcommand `add`/`vouch` to vouch "
                        "for another user. See the help page of the vouch command for more information."
                    )
                else:
                    update.effective_message.reply_text(
                        "You currently vouch for the following users:\n"
                        + "\n".join(f"- {u.name} (ID {u.id}): {self.client.format_balance(u.balance)}" for u in debtors)
                        + "\nUse the subcommands to manage your debtors. See the help page for details."
                    )
            return

        def reply(text: str) -> None:
            keyboard = telegram.InlineKeyboardMarkup([
                [
                    telegram.InlineKeyboardButton(
                        "YES",
                        callback_data=f"vouch {args.command} {args.user.id} {sender_id} accept"
                    ),
                    telegram.InlineKeyboardButton(
                        "NO",
                        callback_data=f"vouch {args.command} {args.user.id} {sender_id} deny"
                    )
                ]
            ])
            util.safe_call(
                lambda: update.effective_message.reply_markdown(text, reply_markup=keyboard),
                lambda: update.effective_message.reply_text(text, reply_markup=keyboard)
            )

        if update.effective_message.chat.type != telegram.Chat.PRIVATE:
            update.effective_message.reply_text("This command should be executed in private chat.")

        elif not args.user.external:
            update.effective_message.reply_text(
                f"This user is not external. Therefore, you can't vouch for {args.user.name}."
            )

        elif args.command in ("add", "vouch"):
            if args.user.voucher_id == sender.id:
                msg = f"You already vouch for {args.user.name}. If you " \
                    "want to stop this, use the command `/vouch stop <username>`."
                util.safe_call(
                    lambda: update.effective_message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN),
                    lambda: update.effective_message.reply_text(msg)
                )

            else:
                reply(
                    f"*Do you really want to vouch for {args.user.name}?*\n\n"
                    "This will have some consequences:\n"
                    "- The external user will become able to perform operations that change "
                    "the balance like sending money or consuming goods.\n"
                    f"- You **must pay all debts** to the community when {args.user.name} "
                    "leaves the community for a longer period or forever or in case you stop "
                    f"vouching for {args.user.name}. On the other side, you will "
                    "get all the virtual money the user had when there's some.\n\n"
                    f"It's recommended to talk to {args.user.name} regularly or check his/her balance."
                )

        elif args.command in ("remove", "stop"):
            if args.user.voucher_id is None:
                update.effective_message.reply_text(
                    "No one is vouching for this user yet. Therefore, you "
                    f"can't remove {args.user.name} from your list of debtors."
                )

            else:
                checkout = self.client.format_balance(abs(args.user.balance))
                reply(
                    f"*Do you really want to stop vouching for {args.user.name}?*\n\n"
                    "This will have some consequences:\n"
                    f"- {args.user.name} won't be able to perform commands that would change "
                    "the balance anymore (e.g. /send or consumption commands).\n"
                    f"- The balance of {args.user.name} will be set to `0`.\n"
                    f"- You will {'pay' if args.user.balance < 0 else 'get'} {checkout} "
                    f"{'to' if args.user.balance < 0 else 'from'} {args.user.name}."
                )


class VouchCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /vouch
    """

    def __init__(self):
        super().__init__(
            "vouch",
            "^vouch",
            {
                "add": self.add,
                "vouch": self.add,
                "remove": self.remove,
                "stop": self.remove
            }
        )

    async def _add(self, update: telegram.Update, debtor: schemas.User, sender: schemas.User):
        try:
            response = await self.client.vouch_for(debtor, sender, sender)
        except exceptions.MateBotSDKException as exc:
            update.callback_query.message.edit_text(exc.message, reply_markup=telegram.InlineKeyboardMarkup([]))
            raise

        update.callback_query.message.edit_text(
            f"You now vouch for {response.debtor.name} (user ID {response.debtor.id}).",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
        update.callback_query.answer(f"You now vouch for {debtor.name}.", show_alert=True)

    async def _remove(self, update: telegram.Update, debtor: schemas.User, sender: schemas.User):
        try:
            response = await self.client.vouch_stop(debtor, sender)
        except exceptions.MateBotSDKException as exc:
            update.callback_query.message.edit_text(exc.message, reply_markup=telegram.InlineKeyboardMarkup([]))
            raise

        ext = f"No transaction was required, since {debtor.name} already had a balance of 0."
        if response.transaction is not None:
            ext = f"A transaction of {self.client.format_balance(response.transaction.amount)} has been made."
        update.callback_query.message.edit_text(
            f"You don't vouch for {debtor.name} anymore. Therefore, the "
            f"privileges of {debtor.name} to use this bot have been limited.\n{ext}",
            reply_markup=telegram.InlineKeyboardMarkup([])
        )
        update.callback_query.answer(f"You don't vouch for {debtor.name} anymore.", show_alert=True)

    async def _handle_vouching(
            self,
            update: telegram.Update,
            func: Callable[[telegram.Update, schemas.User, schemas.User], Awaitable[None]]
    ) -> None:
        _, debtor_id, original_sender, option = self.data.split(" ")
        debtor_id = int(debtor_id)
        original_sender = int(original_sender)
        debtor = await self.client.get_user(debtor_id)
        sender = await self.client.get_core_user(update.callback_query.from_user)

        if update.callback_query.from_user.id != original_sender:
            update.callback_query.answer("Only the creator of this request can answer it!")
            return

        if option == "deny":
            update.callback_query.message.edit_text(
                "You aborted the request.",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
        elif option == "accept":
            self.logger.debug(f"Voucher change request for user {debtor.id} accepted from {sender.name}")
            await func(update, debtor, sender)
        else:
            raise ValueError(f"Invalid query data format: {self.data!r}")

    async def add(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        await self._handle_vouching(update, self._add)

    async def remove(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        await self._handle_vouching(update, self._remove)


@api_callback.dispatcher.register_for(schemas.EventType.VOUCHER_UPDATED)
async def _handle_voucher_updated(event: schemas.Event):
    debtor_id = event.data["id"]
    voucher_id = event.data.get("voucher", None)
    transaction_id = event.data.get("transaction", None)

    voucher = voucher_id and await client.client.get_user(voucher_id)
    transaction = transaction_id and (await client.client.get_transactions(id=transaction_id))[0]

    debtor_telegram = client.client.find_telegram_user(debtor_id)
    voucher_telegram = client.client.find_telegram_user(voucher_id)

    voucher_alias = ""
    if voucher_telegram and voucher_telegram[1]:
        voucher_alias = f" alias @{voucher_telegram[1]}"
    info = ""
    if transaction:
        info = f"\nAdditionally, a payment of {client.client.format_balance(transaction.amount)} has been made."

    if debtor_telegram is not None:
        if voucher_id is None:
            util.safe_call(
                lambda: client.client.bot.send_message(
                    debtor_telegram[0],
                    "Your voucher has been changed. You don't have any active voucher anymore. "
                    f"Therefore, some features of the bot have just been disabled for you.{info}"
                ),
                lambda: None
            )
        elif voucher is not None:
            util.safe_call(
                lambda: client.client.bot.send_message(
                    debtor_telegram[0],
                    f"Good news! You have a new voucher user: {voucher.name}{voucher_alias} now "
                    f"vouches for you and will be held responsible for your actions. See /help for details."
                ),
                lambda: None
            )
