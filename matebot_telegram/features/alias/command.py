"""
MateBot command executor class for /alias
"""

from typing import List

import telegram
from matebot_sdk import schemas

from .. import _app
from ..base import BaseCommand, ExtendedContext, Namespace
from ... import util


def fmt_alias(alias: schemas.Alias, apps: List[schemas.Application]) -> str:
    state = "accepted" if alias.confirmed else "requested (!)"
    try:
        app = f"'{[a for a in apps if a.id == alias.application_id][0].name}'"
    except IndexError:
        app = f"app {alias.application_id}"
    return f"`ID {alias.id}: '{alias.username}' from {app}: {state}`"


class AliasCommand(BaseCommand):
    """
    Command executor for /alias
    """

    def __init__(self):
        super().__init__(
            "alias",
            "Manage your connected user accounts of other applications\n\n"
            "By default, this command shows you currently connected aliases, i.e. available "
            "logins from other applications that have access to your user account. There are "
            "a few subcommands available, e.g. `accept` to verify an alias and make it usable "
            "(because without verification, the connected user account can't be used for any "
            "actions) or `deny` to do the opposite and remove an alias.\nNote that you can't "
            "delete the alias of the currently used application (Telegram). To do this, you "
            "either need to use another application for the action or delete your whole user account."
        )
        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("accept", "deny", "show"),
            type=lambda x: str(x).lower()
        )

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: the custom context of the application
        :type context: ExtendedContext
        :return: None
        """

        if update.effective_chat.type != telegram.Chat.PRIVATE:
            await update.effective_message.reply_text("You should execute this command in private chat only.")
            return

        user = await context.application.client.get_core_user(update.effective_message.from_user)
        if args.subcommand is None or args.subcommand == "show":
            aliases = await context.application.client.get_aliases(user_id=user.id)
            applications = await context.application.client.get_applications()
            msg = f"You currently have the following registered aliases:\n" \
                  + "\n".join([fmt_alias(alias, applications) for alias in aliases])
            await util.safe_call(
                lambda: update.effective_message.reply_markdown_v2(msg),
                lambda: update.effective_message.reply_text(msg)
            )

        elif args.subcommand == "accept":
            aliases = await context.application.client.get_aliases(user_id=user.id, confirmed=False)
            if not aliases:
                await update.effective_message.reply_text("Currently, you have no unconfirmed aliases.")
            else:
                msg = "Here's an overview of currently unconfirmed aliases. Clicking on the button will " \
                      "accept the respective alias and allows the owner of the app's account access to your " \
                      "user account. This includes making transactions, polls, communisms and other features."
                keyboard = [
                    [telegram.InlineKeyboardButton(
                        f"ID {alias.id}: '{alias.username}'",
                        callback_data=f"alias accept {alias.id} {update.effective_message.from_user.id}"
                    )]
                    for alias in aliases
                ] + [[telegram.InlineKeyboardButton("Don't accept any alias now", callback_data=f"alias clear")]]
                await update.effective_message.reply_text(msg, reply_markup=telegram.InlineKeyboardMarkup(keyboard))

        elif args.subcommand == "deny":
            aliases = [
                a for a in await context.application.client.get_aliases(user_id=user.id)
                if a.application_id != _app.client.app_id
            ]
            if not aliases:
                await update.effective_message.reply_text(
                    "Currently, you have no aliases other than the Telegram alias. For safety "
                    "purposes, you can't delete the alias because it would lock you out of your "
                    "account. Use another account to delete the Telegram app alias."
                )
            else:
                msg = "Here's an overview of currently known aliases. Clicking on a button will remove " \
                      "the respective alias and deny the owner of the app's account further access to your " \
                      "user account. This includes making transactions, polls, communisms and other features.\n" \
                      "Note that the current app (Telegram) is not in the list, since deleting it would lock " \
                      "you out of your account. Use another frontend to delete the Telegram app."
                keyboard = [
                    [telegram.InlineKeyboardButton(
                        f"ID {alias.id}: '{alias.username}'",
                        callback_data=f"alias deny {alias.id} {update.effective_message.from_user.id}"
                    )]
                    for alias in aliases
                ] + [[telegram.InlineKeyboardButton("Don't deny any alias now", callback_data=f"alias clear")]]
                await update.effective_message.reply_text(msg, reply_markup=telegram.InlineKeyboardMarkup(keyboard))
