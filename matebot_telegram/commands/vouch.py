"""
MateBot command executor classes for /vouch and its callback queries
"""

import telegram
from matebot_sdk import messages
from matebot_sdk.base import PermissionLevel

from .. import util
from ..base import BaseCommand, BaseCallbackQuery
from ..client import SDK
from ..parsing.types import user_type
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
        p.add_argument("command", choices=("add", "remove"), type=lambda x: str(x).lower())
        p.add_argument("user", type=user_type)

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
        permission_check = SDK.ensure_permissions(user, PermissionLevel.ANY_WITH_VOUCHER, "vouch")
        if not permission_check[0]:
            update.effective_message.reply_text(permission_check[1])
            return

        permission_check = SDK.ensure_permissions(user, PermissionLevel.ANY_INTERNAL, "vouch")
        if args.command is None and not permission_check[0]:
            voucher = SDK.get_username(util.get_event_loop().run_until_complete(SDK.get_user_by_id(user.voucher_id)))
            update.effective_message.reply_text(
                "You're an external user, but you are allowed to interact "
                f"with the bot, since {voucher} vouches for you."
            )
            return

        def reply(text: str) -> None:
            keyboard = telegram.InlineKeyboardMarkup([
                [
                    telegram.InlineKeyboardButton(
                        "YES",
                        callback_data=f"vouch {args.command} {args.user.id} {user.id} accept"
                    ),
                    telegram.InlineKeyboardButton(
                        "NO",
                        callback_data=f"vouch {args.command} {args.user.id} {user.id} deny"
                    )
                ]
            ])
            util.safe_call(
                lambda: update.effective_message.reply_markdown(text, reply_markup=keyboard),
                lambda: update.effective_message.reply_text(text, reply_markup=keyboard)
            )

        all_users = util.get_event_loop().run_until_complete(SDK.get_users())
        if args.command is None:
            debtors = [SDK.get_username(u) for u in all_users if u.voucher_id == user.id]

            if len(debtors) == 0:
                update.effective_message.reply_text(
                    "You don't vouch for any external user at the moment. "
                    "To change this, use `/vouch add|remove <username>`.",
                    parse_mode=telegram.ParseMode.MARKDOWN
                )

            else:
                update.effective_message.reply_text(
                    "You currently vouch for the following user"
                    f"{'s' if len(debtors) != 1 else ''}: {', '.join(debtors)}"
                )

            return

        if update.effective_message.chat.type != telegram.Chat.PRIVATE:
            update.effective_message.reply_text("This command should be executed in private chat.")

        elif not args.user.external:
            update.effective_message.reply_text(
                f"This user is not external. Therefore, you can't vouch for {SDK.get_username(args.user)}."
            )

        elif args.command == "add":
            if args.user.voucher_id == user.id:
                msg = f"You already vouch for {SDK.get_username(args.user)}. If you " \
                    "want to stop this, use the command `/vouch remove <username>`."
                util.safe_call(
                    lambda: update.effective_message.reply_text(msg, parse_mode=telegram.ParseMode.MARKDOWN),
                    lambda: update.effective_message.reply_text(msg)
                )

            elif args.user.voucher_id is not None:
                update.effective_message.reply_text(
                    "Someone else is already vouching for this user. "
                    f"Therefore, you can't vouch for {SDK.get_username(args.user)}."
                )

            else:
                reply(messages.START_VOUCHING_INFORMATION_MARKDOWN.format(debtor=SDK.get_username(args.user)))

        elif args.command == "remove":
            if args.user.voucher_id is None:
                update.effective_message.reply_text(
                    "No one is vouching for this user yet. Therefore, you "
                    f"can't remove {SDK.get_username(args.user)} from your list of debtors."
                )

            elif args.user.voucher_id != user.id:
                update.effective_message.reply_text(
                    "You don't vouch for this user, but someone else does. Therefore, you "
                    f"can't remove {SDK.get_username(args.user)} from your list of debtors."
                )

            else:
                checkout = args.user.balance
                reply(
                    f"*Do you really want to stop vouching for {SDK.get_username(args.user)}?*\n\n"
                    "This will have some consequences:\n"
                    f"- {SDK.get_username(args.user)} won't be able to perform commands that would change "
                    "the balance anymore (e.g. /send or consumption commands).\n"
                    f"- The balance of {SDK.get_username(args.user)} will be set to `0`.\n"
                    f"- You will {'pay' if checkout < 0 else 'get'} {checkout / 100:.2f}€ "
                    f"{'to' if checkout < 0 else 'from'} {SDK.get_username(args.user)}."
                )


class VouchCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /vouch
    """

    def __init__(self):
        super().__init__("vouch", "^vouch", {
            "add": self.add,
            "remove": self.remove
        })

    def add(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        _, debtor_id, voucher_id, option = self.data.split(" ")
        debtor_id = int(debtor_id)
        voucher_id = int(voucher_id)

        debtor = SDK.get_user_by_id(debtor_id)
        voucher = SDK.get_user_by_id(voucher_id)

        sender = util.get_event_loop().run_until_complete(
            SDK.get_user_by_app_alias(str(update.callback_query.from_user.id))
        )
        if sender.id != voucher.id:
            update.callback_query.answer("Only the creator of this request can answer questions!", show_alert=True)
            return

        if option == "deny":
            update.callback_query.message.edit_text(
                "You aborted the request.",
                reply_markup=telegram.InlineKeyboardMarkup([])
            )

        elif option == "accept":
            update.callback_query.answer("Not implemented.")

        else:
            raise ValueError(f"Invalid query data format: {self.data!r}")

    def remove(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        update.callback_query.answer("Not implemented.")

    def run(self, update: telegram.Update) -> None:
        """
        Process or abort the query to add or remove the debtor user

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        try:
            cmd, debtor, creditor, confirmation = self.data.split(" ")
            creditor = MateBotUser(int(creditor))
            debtor = MateBotUser(int(debtor))

            sender = MateBotUser(update.callback_query.from_user)
            if sender != creditor:
                update.callback_query.answer(f"Only the creator of this query can {confirmation} it!")
                return

            if confirmation == "deny":
                text = "_You aborted this operation._"

            elif confirmation == "accept":
                if cmd == "add":
                    text = f"_You now vouch for {debtor.name}._"
                    debtor.creditor = creditor

                elif cmd == "remove":
                    reason = f"vouch: {creditor.name} stopped vouching for {debtor.name}"
                    text = f"_Success. {debtor.name} has no active creditor anymore._"
                    if debtor.balance > 0:
                        text += f"\n_You received {debtor.balance / 100 :.2f}€ from {debtor.name}._"
                        Transaction(debtor, creditor, debtor.balance, reason).commit()
                    elif debtor.balance < 0:
                        text += f"\n_You sent {debtor.balance / 100 :.2f}€ to {debtor.name}._"
                        Transaction(creditor, debtor, debtor.balance, reason).commit()
                    debtor.creditor = None

                else:
                    raise ValueError("Invalid query data")

            else:
                raise ValueError("Invalid query data")

            util.safe_call(
                lambda: update.callback_query.message.reply_text(
                    text,
                    parse_mode="Markdown",
                    reply_to_message=update.callback_query.message
                ),
                lambda: update.callback_query.message.reply_text(
                    text,
                    reply_to_message=update.callback_query.message
                )
            )

            update.callback_query.message.edit_text(
                update.callback_query.message.text_markdown_v2,
                parse_mode="MarkdownV2"
            )

        except (IndexError, ValueError, TypeError, RuntimeError):
            update.callback_query.answer(
                text="There was an error processing your request!",
                show_alert=True
            )
            raise
