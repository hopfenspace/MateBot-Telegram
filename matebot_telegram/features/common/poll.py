"""
MateBot command executor class for /poll
"""

import time
import telegram

from matebot_sdk import schemas

from .. import _common
from ... import client


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
