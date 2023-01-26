"""
API callback handlers for the events POLL_CREATED, POLL_UPDATED and POLL_CLOSED
"""

from matebot_sdk import schemas

from . import common
from .. import _app
from ... import shared_messages


@_app.dispatcher.register_for(schemas.EventType.POLL_CREATED)
async def handle_poll_created(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await _app.client.get_polls(id=poll_id))[0]
    await _app.send_auto_share_messages(
        shared_messages.ShareType.POLL,
        poll_id,
        await common.get_text(_app.client, poll),
        keyboard=common.get_keyboard(poll),
        job_queue=True
    )


@_app.dispatcher.register_for(schemas.EventType.POLL_UPDATED)
async def handle_poll_updated(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await _app.client.get_polls(id=poll_id))[0]
    await _app.update_shared_messages(
        shared_messages.ShareType.POLL,
        poll_id,
        await common.get_text(_app.client, poll),
        keyboard=common.get_keyboard(poll),
        job_queue=True
    )


@_app.dispatcher.register_for(schemas.EventType.POLL_CLOSED)
async def handle_poll_closed(event: schemas.Event):
    poll_id = int(event.data["id"])
    poll = (await _app.client.get_polls(id=poll_id))[0]
    await _app.update_shared_messages(
        shared_messages.ShareType.POLL,
        poll_id,
        await common.get_text(_app.client, poll),
        keyboard=common.get_keyboard(poll),
        delete_shared_messages=True,
        job_queue=True
    )
