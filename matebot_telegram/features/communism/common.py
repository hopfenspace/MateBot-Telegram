

async def get_text(sdk: client.AsyncMateBotSDKForTelegram, communism: schemas.Communism) -> str:
    creator = await sdk.get_user(communism.creator_id)
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
            transaction_count = len(communism.multi_transaction.transactions)
            markdown += (
                f"\n{transaction_count} transaction{('', 's')[transaction_count != 1]} "
                f"{('has', 'have')[transaction_count != 1]} been processed for a total "
                f"value of {sdk.format_balance(communism.multi_transaction.total_amount)}. "
                "Take a look at /history for more details."
            )
        else:
            markdown += "\nThe communism was aborted. No transactions have been processed."

    return markdown


def get_keyboard(communism: schemas.Communism) -> telegram.InlineKeyboardMarkup:
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
            telegram.InlineKeyboardButton("FORWARD", callback_data=f"forward communism {communism.id} ask -1")
        ],
        [
            telegram.InlineKeyboardButton("COMPLETE", callback_data=f("close")),
            telegram.InlineKeyboardButton("ABORT", callback_data=f("abort")),
        ]
    ])

