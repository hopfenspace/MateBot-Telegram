"""
API callback handlers for the events REFUND_CREATED, REFUND_UPDATED and REFUND_CLOSED
"""

from matebot_sdk import schemas

from . import common
from .. import _app
from ... import shared_messages, util


@_app.dispatcher.register_for(schemas.EventType.REFUND_CREATED)
async def handle_refund_created(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await _app.client.get_refunds(id=refund_id))[0]
    await util.send_auto_share_messages(
        _app.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await common.get_text(None, refund),
        keyboard=common.get_keyboard(refund),
        job_queue=_app.job_queue
    )


@_app.dispatcher.register_for(schemas.EventType.REFUND_UPDATED)
async def handle_refund_updated(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await _app.client.get_refunds(id=refund_id))[0]
    util.update_all_shared_messages(
        _app.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await common.get_text(None, refund),
        keyboard=common.get_keyboard(refund),
        job_queue=_app.job_queue
    )


@_app.dispatcher.register_for(schemas.EventType.REFUND_CLOSED)
async def handle_refund_closed(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await _app.client.get_refunds(id=refund_id))[0]
    util.update_all_shared_messages(
        _app.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await common.get_text(None, refund),
        keyboard=common.get_keyboard(refund),
        delete_shared_messages=True,
        job_queue=_app.job_queue
    )
