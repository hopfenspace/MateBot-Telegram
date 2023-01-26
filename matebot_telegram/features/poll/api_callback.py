"""
API callback handlers for the events POLL_CREATED, POLL_UPDATED and POLL_CLOSED
"""

from matebot_sdk import schemas

from .. import _app
from ... import util


@_app.dispatcher.register_for(schemas.EventType.POLL_CREATED)
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


@_app.dispatcher.register_for(schemas.EventType.POLL_UPDATED)
async def handle_poll_updated(event: schemas.Event):
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


@_app.dispatcher.register_for(schemas.EventType.POLL_CLOSED)
async def handle_poll_closed(event: schemas.Event):
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
