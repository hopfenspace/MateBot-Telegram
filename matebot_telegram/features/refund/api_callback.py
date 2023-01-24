

@application.register_for(schemas.EventType.REFUND_CREATED)
async def _handle_refund_created(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await client.client.get_refunds(id=refund_id))[0]
    util.send_auto_share_messages(
        client.client.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await get_text(None, refund),
        keyboard=get_keyboard(refund),
        job_queue=client.client.job_queue
    )


@application.register_for(schemas.EventType.REFUND_UPDATED)
async def _handle_refund_updated(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await client.client.get_refunds(id=refund_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await get_text(None, refund),
        keyboard=get_keyboard(refund),
        job_queue=client.client.job_queue
    )


@application.register_for(schemas.EventType.REFUND_CLOSED)
async def _handle_refund_closed(event: schemas.Event):
    refund_id = int(event.data["id"])
    refund = (await client.client.get_refunds(id=refund_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.REFUND,
        refund_id,
        await get_text(None, refund),
        keyboard=get_keyboard(refund),
        delete_shared_messages=True,
        job_queue=client.client.job_queue
    )
