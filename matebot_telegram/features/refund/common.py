"""
Common utilities for MateBot refund handling
"""

import time

import telegram
from matebot_sdk import schemas

from .. import _app


async def get_text(_, refund: schemas.Refund) -> str:
    approving = [vote.user_name for vote in refund.votes if vote.vote]
    disapproving = [vote.user_name for vote in refund.votes if not vote.vote]
    markdown = (
        f"*Refund by {refund.creator.name}*\n"
        f"Reason: {refund.description}\n"
        f"Amount: {_app.client.format_balance(refund.amount)}\n"
        f"Created: {time.asctime(time.gmtime(refund.created))}\n\n"
        f"*Votes ({len(refund.votes)})*\n"
        f"Proponents ({len(approving)}): {', '.join(approving) or 'None'}\n"
        f"Opponents ({len(disapproving)}): {', '.join(disapproving) or 'None'}\n"
    )

    if refund.active:
        markdown += "\n_The refund request is currently active._"
    elif not refund.active:
        if refund.allowed is not None:
            markdown += f"\n_The request was {('rejected', 'allowed')[refund.allowed]}. "
        else:
            markdown += "\n_The request has been aborted. "
        if refund.transaction:
            markdown += f"The transaction has been processed. Take a look at your history for more details._"
        else:
            markdown += "No transactions have been processed._"
    return markdown


def get_keyboard(refund: schemas.Refund) -> telegram.InlineKeyboardMarkup:
    if not refund.active:
        return telegram.InlineKeyboardMarkup([])
    return telegram.InlineKeyboardMarkup([
        [
            telegram.InlineKeyboardButton("APPROVE", callback_data=f"refund approve {refund.id}"),
            telegram.InlineKeyboardButton("DISAPPROVE", callback_data=f"refund disapprove {refund.id}"),
        ],
        [
            telegram.InlineKeyboardButton("FORWARD", callback_data=f"forward refund {refund.id} ask -1"),
            telegram.InlineKeyboardButton("ABORT", callback_data=f"refund abort {refund.id}")
        ]
    ])
