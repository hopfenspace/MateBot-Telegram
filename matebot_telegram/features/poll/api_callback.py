"""
MateBot command executor class for /poll
"""

import time
import telegram
from typing import Awaitable, Callable, Optional

from matebot_sdk import exceptions, schemas

from . import common
from .. import client, shared_messages, util
from ..api_callback import application
from ..base import BaseCallbackQuery, BaseCommand
from ..parsing.types import any_user_type
from ..parsing.util import Namespace


@application.register_for(schemas.EventType.POLL_CREATED)
async def _handle_poll_created(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await client.client.get_polls(id=poll_id))[0]
    util.send_auto_share_messages(
        client.client.bot,
        shared_messages.ShareType.POLL,
        poll_id,
        await get_text(client.client, poll),
        keyboard=get_keyboard(poll),
        job_queue=client.client.job_queue
    )


@application.register_for(schemas.EventType.POLL_UPDATED)
async def _handle_poll_updated(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await client.client.get_polls(id=poll_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.POLL,
        poll_id,
        await get_text(client.client, poll),
        keyboard=get_keyboard(poll),
        job_queue=client.client.job_queue
    )


@application.register_for(schemas.EventType.POLL_CLOSED)
async def _handle_poll_closed(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await client.client.get_polls(id=poll_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.POLL,
        poll_id,
        await get_text(client.client, poll),
        keyboard=get_keyboard(poll),
        delete_shared_messages=True,
        job_queue=client.client.job_queue
    )
