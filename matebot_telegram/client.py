"""
MateBot SDK client to be used across the project
"""

import asyncio
import logging
from typing import Optional, Union

import telegram

from matebot_sdk.sdk import AsyncSDK
from matebot_sdk.schemas import User as _User

from . import err, persistence, util
from .config import config


logger = logging.getLogger("client")


class AsyncMateBotSDKForTelegram(AsyncSDK):
    bot: telegram.Bot

    @staticmethod
    def patch_user_db_from_update(update: telegram.Update):
        user = update.effective_user
        if user is None:
            return
        if user.is_bot:
            return
        with persistence.get_new_session() as session:
            with session.begin():
                users = [u for u in session.query(persistence.TelegramUser).filter_by(telegram_id=user.id).all()]
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

    async def get_telegram_user(self, identifier: Union[int, str]) -> _User:
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


SDK = AsyncMateBotSDKForTelegram(
    base_url=config["server"],
    app_name=config["application"],
    password=config["password"],
    callback=(config["callback"]["public-url"], config["callback"]["username"], config["callback"]["password"]),
    logger=logging.getLogger("sdk.client")
)


def setup_sdk(bot: telegram.Bot, database_url: str, database_echo: Optional[bool] = None) -> bool:
    logger.debug("Setting up SDK client...")
    if database_echo is None:
        persistence.init(database_url)
    else:
        persistence.init(database_url, echo=database_echo)
    SDK.bot = bot
    if util.event_loop is None:
        logger.error("Event loop uninitialized! Refusing to setup SDK client!")
        return False
    asyncio.run_coroutine_threadsafe(SDK.setup(), loop=util.event_loop).result()
    return True
