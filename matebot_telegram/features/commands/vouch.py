"""
MateBot command executor class for /vouch
"""

import telegram
from matebot_sdk import schemas

from .base import BaseCommand
from .. import _common
from ... import util
from ...parsing.types import any_user_type
from ...parsing.util import Namespace


class VouchCommand(BaseCommand):
    """
    Command executor for /vouch
    """

    def __init__(self):
        super().__init__(
            "vouch",
            "Vouch for other users and show other users' vouchers\n\n"
            "The possible interactions with this bot are pretty limited for external "
            "people for security purposes. If you intend to use this bot, you can ask an "
            "internal user to vouch for you. Doing so gives you the necessary permissions.\n\n"
            "On the other hand, internal users can vouch for externals to allow them to use "
            "this bot. You should note that you will be held responsible in case the user "
            "you are vouching for can't pay possible debts for whatever reason. If the "
            "community decides to disable the external user's account, you have to pay "
            "remaining debts, if there are any. However, you would also get the balance in "
            "case it's positive. After all, you are responsible to deal with the external user.\n\n"
            "This command provides three usages. First, without arguments, it will show your current "
            "debtors or your current voucher. Second, with one argument, it shows you the voucher "
            "of one particular user. Note that you need have sufficient permissions to use that "
            "command. Third, with two arguments you can manage your debtors. The first needs to be "
            "a command like `start` to begin vouching for someone and `stop` to do the opposite. The "
            "second argument is the user you want to vouch or stop vouching for."
        )

        p1 = self.parser.new_usage()
        p1.add_argument("user", type=any_user_type)
        p2 = self.parser.new_usage()
        p2.add_argument("command", choices=("add", "start", "remove", "stop"), type=lambda x: str(x).lower())
        p2.add_argument("user", type=any_user_type)

    async def run(self, args: Namespace, update: telegram.Update, context: _common.ExtendedContext) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: _common.ExtendedContext
        :return: None
        """

        sender_id = update.effective_message.from_user.id
        sender = await context.application.client.get_core_user(update.effective_message.from_user)

        if args.command is None:
            if args.user is not None:
                if sender.privilege < schemas.PrivilegeLevel.INTERNAL:
                    await update.effective_message.reply_text("You are not permitted to use this feature.")
                elif args.user.external:
                    if args.user.voucher_id:
                        voucher = await context.application.client.get_user(args.user.voucher_id)
                        await update.effective_message.reply_text(f"Currently, {voucher.name} vouches for {args.user.name}.")
                    else:
                        await update.effective_message.reply_text(f"Nobody vouches for {args.user.name} at the moment.")
                else:
                    debtors = await context.application.client.get_users(voucher_id=args.user.id)
                    if not debtors:
                        await update.effective_message.reply_text(f"{args.user.name} vouches for nobody at the moment.")
                    else:
                        await update.effective_message.reply_text(f"{args.user.name} vouches for {len(debtors)} other users.")
                return
            if sender.voucher_id is not None:
                assert sender.external
                voucher = await context.application.client.get_user(sender.voucher_id)
                await update.effective_message.reply_text(
                    "You're an external user, but you are allowed to interact "
                    f"with the bot, since {voucher.name} vouches for you."
                )
            elif sender.external:
                await update.effective_message.reply_text("You need a voucher to use this and some other bot features.")
            else:
                debtors = await context.application.client.get_users(voucher_id=sender.id)
                if not debtors:
                    await update.effective_message.reply_markdown(
                        "You currently don't vouch for anybody. Use the subcommand `add` or `start` to vouch "
                        "for another user. See the help page of the vouch command for more information."
                    )
                else:
                    await update.effective_message.reply_text(
                        "You currently vouch for the following users:\n"
                        + "\n".join(f"- {u.name} (ID {u.id}): {context.application.client.format_balance(u.balance)}" for u in debtors)
                        + "\nUse the subcommands to manage your debtors. See the help page for details."
                    )
            return

        async def reply(text: str) -> None:
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
            await util.safe_call(
                lambda: update.effective_message.reply_markdown(text, reply_markup=keyboard),
                lambda: update.effective_message.reply_text(text, reply_markup=keyboard)
            )

        if update.effective_message.chat.type != telegram.Chat.PRIVATE:
            await update.effective_message.reply_text("This command should be executed in private chat.")

        elif not args.user.external:
            await update.effective_message.reply_text(
                f"This user is not external. Therefore, you can't vouch for {args.user.name}."
            )

        elif args.command in ("add", "start"):
            if args.user.voucher_id == sender.id:
                msg = f"You already vouch for {args.user.name}. If you " \
                    "want to stop this, use the command `/vouch stop <username>`."
                await util.safe_call(
                    lambda: update.effective_message.reply_text(msg, parse_mode=telegram.constants.ParseMode.MARKDOWN),
                    lambda: update.effective_message.reply_text(msg)
                )

            else:
                await reply(
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
                await update.effective_message.reply_text(
                    "No one is vouching for this user yet. Therefore, you "
                    f"can't remove {args.user.name} from your list of debtors."
                )

            else:
                checkout = context.application.client.format_balance(abs(args.user.balance))
                await reply(
                    f"*Do you really want to stop vouching for {args.user.name}?*\n\n"
                    "This will have some consequences:\n"
                    f"- {args.user.name} won't be able to perform commands that would change "
                    "the balance anymore (e.g. /send or consumption commands).\n"
                    f"- The balance of {args.user.name} will be set to `0`.\n"
                    f"- You will {'pay' if args.user.balance < 0 else 'get'} {checkout} "
                    f"{'to' if args.user.balance < 0 else 'from'} {args.user.name}."
                )
