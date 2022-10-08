"""
MateBot SDK client to be used across the project
"""

import asyncio
import logging
from typing import Optional, Tuple, Union

import telegram.ext

from matebot_sdk.sdk import AsyncSDK
from matebot_sdk.schemas import User as _User

from . import config, err, util, persistence, shared_messages as _shared_messages


logger = logging.getLogger("client")


class AsyncMateBotSDKForTelegram(AsyncSDK):
    bot: telegram.Bot
    job_queue: telegram.ext.JobQueue
    shared_messages: _shared_messages.SharedMessageHandler

    def __init__(self, dispatcher: telegram.ext.Dispatcher, *args, **kwargs):
        super(AsyncMateBotSDKForTelegram, self).__init__(*args, **kwargs)
        self._dispatcher = dispatcher
        self.bot = dispatcher.bot
        self.job_queue = dispatcher.job_queue
        self.shared_messages = _shared_messages.SharedMessageHandler()

    @staticmethod
    def get_new_session() -> persistence.Session:
        return persistence.get_new_session()

    @staticmethod
    def format_balance(balance_or_user: Union[int, float, _User]):
        if isinstance(balance_or_user, _User):
            balance_or_user = balance_or_user.balance
        v = balance_or_user / config.config.currency.factor
        return f"{v:.{config.config.currency.digits}f}{config.config.currency.symbol}"

    @staticmethod
    def patch_user_db_from_update(update: telegram.Update):
        user = update.effective_user
        if user is None or user.is_bot:
            return
        with persistence.get_new_session() as session:
            with session.begin():
                users = session.query(persistence.TelegramUser).filter_by(telegram_id=user.id).all()
                if len(users) == 1:
                    db_user = users[0]
                    db_user.first_name = user.first_name
                    db_user.last_name = user.last_name
                    db_user.username = user.username
                    session.add(db_user)
                    session.commit()
                elif len(users) > 1:
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
        raise err.AmbiguousUserSpec(f"Multiple users found for '{identifier}'. Please ensure unambiguous usernames.")

    async def _ensure_not_existing(self, session: persistence.Session, telegram_user: telegram.User) -> Optional[_User]:
        existing_user = session.query(persistence.TelegramUser).get(telegram_user.id)
        if existing_user is not None:
            record = session.query(persistence.RegistrationProcess).get(telegram_user.id)
            if record is not None:
                session.delete(record)
                session.commit()
            return await self.get_user(existing_user.user_id)
        return None

    @staticmethod
    def _handle_new_user_update(user_id: int, telegram_user: telegram.User, session: persistence.Session):
        record = session.query(persistence.RegistrationProcess).get(telegram_user.id)
        if record is not None:
            session.delete(record)
        session.commit()
        session.add(persistence.TelegramUser(
            telegram_id=telegram_user.id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            user_id=user_id
        ))
        session.commit()

    async def sign_up_as_alias(self, telegram_user: telegram.User, core_user_id: int) -> _User:
        with self.get_new_session() as session:
            existing_user = await self._ensure_not_existing(session, telegram_user)
            if existing_user is not None:
                return existing_user
            alias = await self.create_alias(core_user_id, str(telegram_user.id), confirmed=False)
            self._handle_new_user_update(alias.user_id, telegram_user, session)
            return await self.get_user(alias.user_id)

    async def sign_up_new_user(self, telegram_user: telegram.User, username: str) -> _User:
        with self.get_new_session() as session:
            existing_user = await self._ensure_not_existing(session, telegram_user)
            if existing_user is not None:
                return existing_user
            user = await super().create_app_user(username, str(telegram_user.id), True)
            self._handle_new_user_update(user.id, telegram_user, session)
            return user

    def find_telegram_user(self, core_id: int) -> Optional[Tuple[int, Optional[str]]]:
        with self.get_new_session() as session:
            users = session.query(persistence.TelegramUser).filter_by(user_id=core_id).all()
            if len(users) == 1:
                return users[0].telegram_id, users[0].username
        return None

    async def get_core_user(self, identifier: Union[int, str, telegram.User]) -> _User:
        pretty = None
        if isinstance(identifier, telegram.User):
            pretty = identifier.username or identifier.first_name
            identifier = identifier.id
        if isinstance(identifier, str):
            pretty = identifier
            try:
                identifier = self._lookup_telegram_identifier(identifier)
            except err.NoUserFound as exc:
                users = await self.get_users(name=identifier)
                if users and len(users) == 1:
                    if [a for a in users[0].aliases if a.confirmed and a.application_id == self.app_id]:
                        return users[0]
                    if [a for a in users[0].aliases if a.application_id == self.app_id]:
                        raise err.UserNotVerified(
                            f"The user alias for {users[0].name} is not confirmed yet. It can't be "
                            "used while the connection to the other MateBot apps wasn't verified."
                        ) from exc
                raise
        users = await self.get_users_by_alias(alias=str(identifier), confirmed=True, active=True)
        if len(users) == 1:
            return users[0]
        users = await self.get_users_by_alias(alias=str(identifier), confirmed=False, active=True)
        if len(users) == 1:
            raise err.UserNotVerified(
                f"The user alias for {users[0].name} is not confirmed yet. It can't be "
                "used while the connection to the other MateBot apps wasn't verified."
            )
        if len(users) == 0:
            raise err.UniqueUserNotFound(
                f"No user was found as {pretty or identifier}. Make sure the username is correct "
                "and the user recently used the bot. Try sending /start to the bot privately."
            )
        raise err.UniqueUserNotFound(f"Multiple users were found for {pretty or identifier}. Please file a bug report.")


client: AsyncMateBotSDKForTelegram  # must be available at runtime; use the setup function below at early program stage


def setup(updater: telegram.ext.Updater, configuration: config.Configuration) -> AsyncMateBotSDKForTelegram:
    logger.debug("Setting up SDK client...")
    persistence.init(configuration.database_url, echo=configuration.database_debug)
    if util.event_loop is None:
        logger.error("Event loop uninitialized! Refusing to setup SDK client!")
        raise RuntimeError("Uninitialized event loop")

    callback = None
    if configuration.callback.enabled:
        callback = (configuration.callback.public_url, configuration.callback.shared_secret)
    sdk = AsyncMateBotSDKForTelegram(
        updater.dispatcher,
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
