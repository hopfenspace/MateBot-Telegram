"""
API callback handler for the event USER_UPDATED
"""

from matebot_sdk import schemas

from .. import _app


@_app.dispatcher.register_for(schemas.EventType.USER_UPDATED)
async def handle_user_softly_deleted(_: schemas.Event):
    # TODO: Implement this in case PTB's `user_data` is used purposefully; currently unnecessary function
    pass
