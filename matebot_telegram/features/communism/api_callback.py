"""
API callback handlers for the events COMMUNISM_CREATED, COMMUNISM_UPDATED and COMMUNISM_CLOSED
"""

from matebot_sdk import schemas

from . import common
from .. import _app
from ... import shared_messages


@_app.dispatcher.register_for(schemas.EventType.COMMUNISM_CREATED)
async def handle_communism_created(event: schemas.Event):
    communism_id = int(event.data["id"])
    communism = (await _app.client.get_communisms(id=communism_id))[0]
    await _app.send_auto_share_messages(
        shared_messages.ShareType.COMMUNISM,
        communism_id,
        await common.get_text(_app.client, communism),
        keyboard=common.get_keyboard(communism),
        job_queue=True
    )


@_app.dispatcher.register_for(schemas.EventType.COMMUNISM_UPDATED)
async def handle_communism_updated(event: schemas.Event):
    communism_id = int(event.data["id"])
    communism = (await _app.client.get_communisms(id=communism_id))[0]
    await _app.update_shared_messages(
        shared_messages.ShareType.COMMUNISM,
        communism_id,
        await common.get_text(_app.client, communism),
        keyboard=common.get_keyboard(communism),
        job_queue=True
    )


@_app.dispatcher.register_for(schemas.EventType.COMMUNISM_CLOSED)
async def handle_communism_closed(event: schemas.Event):
    communism_id = int(event.data["id"])
    communism = (await _app.client.get_communisms(id=communism_id))[0]
    await _app.update_shared_messages(
        shared_messages.ShareType.COMMUNISM,
        communism_id,
        await common.get_text(_app.client, communism),
        keyboard=common.get_keyboard(communism),
        delete_shared_messages=True,
        job_queue=True
    )
