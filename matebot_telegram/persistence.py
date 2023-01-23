"""
PTB's persistence implementation using SQLAlchemy

The data format for a single keyboard looks like the following snippet:

    ('b5bdc3dd9f384c279f94415db69f97ec',
      1674437121.2438297,
      {'2938f767fa404473982587493f3d81ec': 'some callback data text 1',
       '680c5f8dd52d4e839e0320f2e289b210': 'some callback data text 2'})
"""

import logging
from typing import Dict, List, Optional

import telegram.ext
import sqlalchemy.exc
from telegram.ext._utils.types import BD, CD, CDCData, ConversationDict, ConversationKey, UD

from . import models as _models
from .database import get_new_session, Session


def _get_callback_data(session: Session) -> CDCData:
    """
    Load the callback data from the database (this is usually done once at program startup)
    """

    existing_keyboards: List[_models.CallbackKeyboard] = session.query(_models.CallbackKeyboard).all()
    # TODO: in case the button order is messed up, here's the place to check it
    keyboards = [
        (k.keyboard_id, k.creation_time, {b.button_id: b.button_text for b in k.buttons})
        for k in existing_keyboards
    ]
    queries: List[_models.CallbackQuery] = session.query(_models.CallbackQuery).all()
    return keyboards, {str(q.query_id): q.keyboard_id for q in queries}


def _update_callback_data(session: Session, data: CDCData) -> None:
    """
    Store the updated callback data in the database
    """

    keyboards, queries = data
    keyboard_ids = [k[0] for k in keyboards]

    # Updating the keyboards requires to check all existing queries to drop the vanished
    existing_keyboards: List[_models.CallbackKeyboard] = session.query(_models.CallbackKeyboard).all()
    known_keyboard_ids = []
    for k in existing_keyboards:
        if k.keyboard_id not in keyboard_ids:
            session.delete(k)
        else:
            known_keyboard_ids.append(k.keyboard_id)
    session.add_all(
        _models.CallbackKeyboard(keyboard_id=k[0], creation_time=k[1], buttons=[
            _models.CallbackButton(button_id=b, button_text=str(t), keyboard_place=i)
            for i, (b, t) in enumerate(k[2].items())
        ])
        for k in keyboards
        if k[0] not in known_keyboard_ids
    )

    # Updating the queries requires to check all existing queries to drop the vanished
    existing_queries: List[_models.CallbackQuery] = session.query(_models.CallbackQuery).all()
    known_query_ids: List[str] = []
    for q in existing_queries:
        if str(q.query_id) not in queries:
            session.delete(q)
        else:
            known_query_ids.append(str(q.query_id))
    session.add_all(
        _models.CallbackQuery(query_id=k, keyboard_id=v)
        for k, v in queries.items()
        if k not in known_query_ids
    )

    session.commit()


class BotPersistence(telegram.ext.BasePersistence):
    """
    PTB persistence handler for arbitrary callback data and user data
    """

    # TODO: Implement handling of user data, this is currently unimplemented and unused

    def __init__(self, logger: logging.Logger, update_interval: float = 60):
        super().__init__(telegram.ext.PersistenceInput(bot_data=False, chat_data=False), update_interval)
        self.logger = logger

    async def get_user_data(self) -> Dict[int, UD]:
        return {}

    async def update_user_data(self, user_id: int, data: UD) -> None:
        pass

    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        pass

    async def drop_user_data(self, user_id: int) -> None:
        pass

    async def get_callback_data(self) -> Optional[CDCData]:
        try:
            with get_new_session() as session:
                return _get_callback_data(session)
        except sqlalchemy.exc.SQLAlchemyError:
            self.logger.exception("Failed to load callback data from the 'get_callback_data' handler")
            raise

    async def update_callback_data(self, data: CDCData) -> None:
        try:
            with get_new_session() as session:
                return _update_callback_data(session, data)
        except sqlalchemy.exc.SQLAlchemyError:
            self.logger.exception("Failed to store callback data in the 'update_callback_data' handler")
            raise

    async def flush(self) -> None:
        pass

    # Below are the features that are not required and therefore not implemented

    async def get_bot_data(self) -> BD:
        pass

    async def update_bot_data(self, data: BD) -> None:
        pass

    async def refresh_bot_data(self, bot_data: BD) -> None:
        pass

    async def get_chat_data(self) -> Dict[int, CD]:
        pass

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        pass

    async def get_conversations(self, name: str) -> ConversationDict:
        pass

    async def update_conversation(self, name: str, key: ConversationKey, new_state: Optional[object]) -> None:
        pass
