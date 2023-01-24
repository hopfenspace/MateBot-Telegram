
@application.register_for(schemas.EventType.COMMUNISM_CREATED)
async def _handle_communism_created(event: schemas.Event):
    communism_id = int(event.data["id"])
    communism = (await client.client.get_communisms(id=communism_id))[0]
    util.send_auto_share_messages(
        client.client.bot,
        shared_messages.ShareType.COMMUNISM,
        communism_id,
        await get_text(client.client, communism),
        keyboard=get_keyboard(communism),
        job_queue=client.client.job_queue
    )


@application.register_for(schemas.EventType.COMMUNISM_UPDATED)
async def _handle_communism_updated(event: schemas.Event):
    communism_id = int(event.data["id"])
    communism = (await client.client.get_communisms(id=communism_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.COMMUNISM,
        communism_id,
        await get_text(client.client, communism),
        keyboard=get_keyboard(communism),
        job_queue=client.client.job_queue
    )


@application.register_for(schemas.EventType.COMMUNISM_CLOSED)
async def _handle_communism_closed(event: schemas.Event):
    communism_id = int(event.data["id"])
    communism = (await client.client.get_communisms(id=communism_id))[0]
    util.update_all_shared_messages(
        client.client.bot,
        shared_messages.ShareType.COMMUNISM,
        communism_id,
        await get_text(client.client, communism),
        keyboard=get_keyboard(communism),
        delete_shared_messages=True,
        job_queue=client.client.job_queue
    )
