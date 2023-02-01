"""
MateBot SDK client to be used across the project
"""

from typing import Optional, Tuple, Union

import httpx
import telegram.ext

from matebot_sdk.sdk import AsyncSDK
from matebot_sdk.schemas import User as _User

# Note that there's another import in the `format_balance` staticmethod
from . import config, database, err, models, shared_messages as _shared_messages


class AsyncMateBotSDKForTelegram(AsyncSDK):
    shared_messages: _shared_messages.SharedMessageHandler

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shared_messages = _shared_messages.SharedMessageHandler()

    async def check_telegram_connectivity(self, conf: config.Configuration, timeout: Optional[float] = None) -> bool:
        """
        Try reaching the Telegram API manually to verify its connectivity
        """

        try:
            self._logger.debug("Trying to connect to the Telegram API manually to verify connectivity ...")
            if timeout:
                r = await self._client.get(f"https://api.telegram.org/bot{conf.token}/getme", timeout=timeout)
            else:
                r = await self._client.get(f"https://api.telegram.org/bot{conf.token}/getme")
            r.raise_for_status()
        except httpx.HTTPError as exc:
            self._logger.warning(f"Verifying connectivity to Telegram API failed: {exc!r}")
            return False
        return True

    @classmethod
    def get_new_session(cls) -> database.Session:
        return database.get_new_session()

    @classmethod
    def format_balance(cls, balance_or_user: Union[int, float, _User]):
        from .application import get_running_app
        currency = get_running_app().config.currency
        if isinstance(balance_or_user, _User):
            balance_or_user = balance_or_user.balance
        v = balance_or_user / currency.factor
        return f"{v:.{currency.digits}f}{currency.symbol}"

    @classmethod
    def patch_user_db_from_update(cls, update: telegram.Update):
        user = update.effective_user
        if user is None or user.is_bot:
            return
        with database.get_new_session() as session:
            with session.begin():
                users = session.query(models.TelegramUser).filter_by(telegram_id=user.id).all()
                if len(users) == 1:
                    db_user = users[0]
                    db_user.first_name = user.first_name
                    db_user.last_name = user.last_name
                    db_user.username = user.username
                    session.add(db_user)
                    session.commit()
                elif len(users) > 1:
                    raise RuntimeError(f"Multiple user results for telegram ID {user.id}! Please file a bug report.")

    @classmethod
    def _lookup_telegram_identifier(cls, identifier: str) -> int:
        with database.get_new_session() as session:
            with session.begin():
                if identifier.startswith("@"):
                    identifier = identifier[1:]
                users_by_username = session.query(models.TelegramUser).filter_by(username=identifier).all()
                users_by_first_name = session.query(models.TelegramUser).filter_by(first_name=identifier).all()
                users_by_full_name = []
                if identifier.count(" ") == 1:
                    first, last = identifier.split(" ")
                    users_by_full_name = session.query(models.TelegramUser).filter_by(
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

    async def _ensure_not_existing(self, session: database.Session, telegram_user: telegram.User) -> Optional[_User]:
        existing_user = session.query(models.TelegramUser).get(telegram_user.id)
        if existing_user is not None:
            record = session.query(models.RegistrationProcess).get(telegram_user.id)
            if record is not None:
                session.delete(record)
                session.commit()
            return await self.get_user(existing_user.user_id)
        return None

    @classmethod
    def _handle_new_user_update(cls, user_id: int, telegram_user: telegram.User, session: database.Session):
        record = session.query(models.RegistrationProcess).get(telegram_user.id)
        if record is not None:
            session.delete(record)
        session.commit()
        session.add(models.TelegramUser(
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
        """
        Find a Telegram user ID with optional Telegram username by a given core ID, if any
        """

        with self.get_new_session() as session:
            users = session.query(models.TelegramUser).filter_by(user_id=core_id).all()
            if len(users) == 1:
                return users[0].telegram_id, users[0].username
        return None

    async def get_core_user(
            self,
            identifier: Union[int, str, telegram.User],
            foreign_user: bool = False,
            community: bool = False
    ) -> _User:
        """
        Lookup core user by identifier (core ID, core username, Telegram user or any unique alias username)

        If `foreign_user` is set, a single core user which isn't known in this app, can be
        returned; otherwise NoUserFound. If `community` is set, the community user may be returned.
        """

        pretty = None
        if isinstance(identifier, telegram.User):
            pretty = f"@{identifier.username}" or identifier.first_name
            identifier = identifier.id
        if isinstance(identifier, str):
            pretty = identifier
            try:
                identifier = self._lookup_telegram_identifier(identifier)
            except err.NoUserFound as exc:
                users = await self.get_users(name=identifier, community=community)
                if users and len(users) == 1:
                    if [a for a in users[0].aliases if a.confirmed and a.application_id == self.app_id] or foreign_user:
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
