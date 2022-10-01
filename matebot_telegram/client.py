"""
MateBot SDK client to be used across the project
"""

import asyncio
import logging
from typing import Union

import telegram

from matebot_sdk.sdk import AsyncSDK
from matebot_sdk.schemas import User as _User

from . import config, err, util, persistence


logger = logging.getLogger("client")


class AsyncMateBotSDKForTelegram(AsyncSDK):
    bot: telegram.Bot

    def __init__(self, bot: telegram.Bot, *args, **kwargs):
        super(AsyncMateBotSDKForTelegram, self).__init__(*args, **kwargs)
        self.bot = bot

    @staticmethod
    def patch_user_db_from_update(update: telegram.Update):
        user = update.effective_user
        if user is None or user.is_bot:
            return
        with persistence.get_new_session() as session:
            with session.begin():
                users = session.query(persistence.TelegramUser).filter_by(telegram_id=user.id).all()
                if len(users) == 0:
                    session.add(persistence.TelegramUser(
                        telegram_id=user.id,
                        user_id=None,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        username=user.username
                    ))
                elif len(users) == 1:
                    db_user = users[0]
                    db_user.first_name = user.first_name
                    db_user.last_name = user.last_name
                    db_user.username = user.username
                    session.add(db_user)
                else:
                    raise RuntimeError(f"Multiple user results for telegram ID {user.id}! Please file a bug report.")

    @staticmethod
    def _lookup_telegram_identifier(identifier: str) -> int:
        with persistence.get_new_session() as session:
            with session.begin():
                if identifier.startswith("@"):
                    identifier = identifier[1:]
                users_by_username = session.query(persistence.TelegramUser).filter_by(username=identifier).all()
                users_by_first_name = session.query(persistence.TelegramUser).filter_by(first_name=identifier).all()
                users_by_full_name = []
                if identifier.count(" ") == 1:
                    first, last = identifier.split(" ")
                    users_by_full_name = session.query(persistence.TelegramUser).filter_by(
                        first_name=first, last_name=last
                    ).all()
                users = set(users_by_username) | set(users_by_first_name) | set(users_by_full_name)
                if len(users) == 1:
                    return users.pop().telegram_id
                if len(users) == 0:
                    raise err.NoUserFound(
                        f"No user found for the search term '{identifier}'. Please ensure "
                        f"you spelled it correctly and the user has used the bot in the past."
                    )
        raise err.AmbiguousUserSpec(f"Multiple users found for '{identifier}'. Please ensure unambiguous specs.")

    async def get_core_user(self, identifier: Union[int, str, telegram.User]) -> _User:
        if isinstance(identifier, telegram.User):
            identifier = identifier.id
        if isinstance(identifier, str):
            identifier = self._lookup_telegram_identifier(identifier)
        users = await self.get_users_by_alias(alias=str(identifier), confirmed=True, active=True)
        if len(users) == 1:
            return users[0]
        users = await self.get_users_by_alias(alias=str(identifier), confirmed=False, active=True)
        if len(users) == 1:
            raise err.UniqueUserNotFound(f"The user alias of {identifier} for {users[0].name} is not confirmed yet.")
        if len(users) == 0:
            raise err.UniqueUserNotFound(f"No user alias was found for {identifier}. Please create a new alias first.")
        raise err.UniqueUserNotFound(f"Multiple user aliases were found for {identifier}. Please file a bug report.")


client: AsyncMateBotSDKForTelegram  # must be available at runtime; use the setup function below at early program stage


def setup(bot: telegram.Bot, configuration: config.Configuration) -> AsyncMateBotSDKForTelegram:
    logger.debug("Setting up SDK client...")
    persistence.init(configuration.database_url, echo=configuration.database_debug)
    if util.event_loop is None:
        logger.error("Event loop uninitialized! Refusing to setup SDK client!")
        raise RuntimeError("Uninitialized event loop")

    callback = None
    if configuration.callback.enabled:
        callback = (configuration.callback.public_url, configuration.callback.shared_secret)
    sdk = AsyncMateBotSDKForTelegram(
        bot,
        base_url=configuration.server,
        app_name=configuration.application,
        password=configuration.password,
        callback=callback,
        logger=logging.getLogger("sdk.client"),
        verify=configuration.ssl_verify and (configuration.ca_path or True),
        user_agent=configuration.user_agent or None
    )

    asyncio.run_coroutine_threadsafe(sdk.setup(), loop=util.event_loop).result()
    logger.debug("Completed SDK setup")
    return sdk
