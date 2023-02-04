"""
MateBot command executor classes for /send and its callback queries
"""

import telegram

from ...base import BaseCommand, ExtendedContext, Namespace, RLArgs, types


class SendCommand(BaseCommand):
    """
    Command executor for /send
    """

    def __init__(self):
        super().__init__(
            "send",
            "Send money to another user\n\n"
            "Performing this command allows you to send money to someone else. "
            "Obviously, the receiver of your transaction has to be registered with "
            "this bot. For security purposes, the bot will ask you to confirm your "
            "proposed transaction before the virtual money will be transferred.\n\n"
            "The first and second argument, `amount` and `receiver` respectively, are "
            "mandatory. But you can add as many extra words as you want afterwards. "
            "Those are treated as description/reason for your transaction."
        )

        self.parser.add_argument("amount", type=types.amount_type)
        self.parser.add_argument("receiver", type=types.any_user_type)
        self.parser.add_argument("reason", default="<no description>", nargs="*")
        second_usage = self.parser.new_usage()
        second_usage.add_argument("receiver", type=types.any_user_type)
        second_usage.add_argument("amount", type=types.amount_type)
        second_usage.add_argument("reason", default="<no description>", nargs="*")

    async def run(self, args: Namespace, update: telegram.Update, context: ExtendedContext) -> None:
        """
        Allow users to send money to other users via a inline keyboard to accept the transaction
        """

        if isinstance(args.reason or [], list):
            reason = "send: " + " ".join(map(str, args.reason))
        else:
            reason = "send: " + str(args.reason)

        issuer = await context.application.client.get_core_user(update.effective_message.from_user)
        if issuer.privilege < issuer.privilege.VOUCHED:
            await update.effective_message.reply_text(
                "You are not permitted to use this feature. See /help for details."
            )
            return

        def e(variant: str) -> str:
            return f"send {variant} {args.amount} {update.effective_message.from_user.id} {args.receiver.id}"

        formatted_amount = context.application.client.format_balance(args.amount)
        keyboard = telegram.InlineKeyboardMarkup([[
            telegram.InlineKeyboardButton("CONFIRM", callback_data=e("confirm")),
            telegram.InlineKeyboardButton("ABORT", callback_data=e("abort"))
        ]])
        try:
            await context.bot.send_message(
                update.effective_message.chat_id,
                f"Do you want to send {formatted_amount} to {args.receiver.name}?\nDescription: `{reason}`",
                disable_web_page_preview=True,
                parse_mode=telegram.constants.ParseMode.MARKDOWN,
                reply_to_message_id=update.effective_message.message_id,
                reply_markup=keyboard,
                rate_limit_args=RLArgs(fix_parser_errors=False)
            )
        except telegram.error.BadRequest as exc:
            self.logger.warning(f"BadRequest during send: {exc!s}")
            await update.effective_message.reply_text(
                f"Do you want to send {formatted_amount} to {args.receiver.name}?\n\n"
                f"Attention: Since your description contains un-parseable characters like underscores "
                f"or apostrophes, the description '<no reason>' will be used as a fallback value.",
                reply_markup=keyboard
            )
