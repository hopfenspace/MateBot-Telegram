"""
MateBot telegram shared message library
"""

import enum
import threading
from typing import List, Optional

import pydantic

from . import database, models


@enum.unique
class ShareType(enum.Enum):
    ALIAS = "alias"
    COMMUNISM = "communism"
    POLL = "poll"
    REFUND = "refund"


class SharedMessage(pydantic.BaseModel):
    share_type: ShareType
    share_id: int
    chat_id: int
    message_id: int

    @staticmethod
    def from_model(model: models.SharedMessage) -> "SharedMessage":
        return SharedMessage(
            share_type=ShareType(model.share_type),
            share_id=model.share_id,
            chat_id=model.chat_id,
            message_id=model.message_id
        )


class SharedMessageHandler:
    """
    Handler for shared messages across multiple unique telegram chats
    """

    def __init__(self):
        self._lock = threading.Lock()

    def get_messages(
            self,
            share_type: Optional[ShareType] = None,
            share_id: Optional[int] = None
    ) -> List[SharedMessage]:
        """
        Get all messages, optionally filtering by share type and share ID
        """

        if share_type is None and share_id is not None:
            raise ValueError("ShareType can't be unset when the share ID is set")
        with self._lock:
            with database.get_new_session() as session:
                query = session.query(models.SharedMessage)
                if share_type:
                    query = query.filter_by(share_type=share_type.value)
                    if share_id:
                        query = query.filter_by(share_id=share_id)
                return [SharedMessage.from_model(model) for model in query.all()]

    def add_message(self, shared_message: SharedMessage) -> bool:
        return self.add_message_by(**shared_message.dict())

    def add_message_by(self, share_type: ShareType, share_id: int, chat_id: int, message_id: int) -> bool:
        """
        Add a new shared message; return True if a new message was created, False otherwise
        """

        with self._lock:
            with database.get_new_session() as session:
                if session.query(models.SharedMessage).filter_by(
                    share_type=share_type.value,
                    share_id=share_id,
                    chat_id=chat_id,
                    message_id=message_id
                ).all():
                    return False
                session.add(models.SharedMessage(
                    share_type=share_type.value,
                    share_id=share_id,
                    chat_id=chat_id,
                    message_id=message_id
                ))
                session.commit()
        return True

    def delete_message(self, shared_message: SharedMessage) -> bool:
        return self.delete_message_by(**shared_message.dict())

    def delete_message_by(self, share_type: ShareType, share_id: int, chat_id: int, message_id: int) -> bool:
        """
        Delete the specified shared message; return True when anything was deleted, False otherwise
        """

        with self._lock:
            with database.get_new_session() as session:
                messages = session.query(models.SharedMessage).filter_by(
                    share_type=share_type.value,
                    share_id=share_id,
                    chat_id=chat_id,
                    message_id=message_id
                ).all()
                if not messages:
                    return False
                for m in messages:
                    session.delete(m)
                session.commit()
        return True

    def delete_messages(self, share_type: ShareType, share_id: int) -> bool:
        """
        Delete all specified shared messages; return True when anything was deleted, False otherwise
        """

        with self._lock:
            with database.get_new_session() as session:
                messages = session.query(models.SharedMessage).filter_by(
                    share_type=share_type.value,
                    share_id=share_id
                ).all()
                if not messages:
                    return False
                for m in messages:
                    session.delete(m)
                session.commit()
        return True

    def pop_all_messages_by_chat(self, chat_id: int) -> List[SharedMessage]:
        """
        Delete and return all shared messages with a common chat ID, regardless of share type or ID
        """

        with self._lock:
            with database.get_new_session() as session:
                messages = session.query(models.SharedMessage).filter_by(chat_id=chat_id).all()
                results = [SharedMessage.from_model(model) for model in messages]
                for m in messages:
                    session.delete(m)
                session.commit()
                return results
