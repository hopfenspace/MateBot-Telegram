"""
MateBot telegram persistence library
"""

from datetime import datetime as _dt

from sqlalchemy import BigInteger, Column, DateTime, FetchedValue, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func


Base = declarative_base()


class TelegramUser(Base):
    """
    Model representing one end-user alias bind to a MateBot user
    """

    __tablename__ = "telegram_users"

    telegram_id: int = Column(BigInteger, nullable=False, primary_key=True, unique=True)
    user_id: int = Column(BigInteger, nullable=False, unique=True)
    first_name: str = Column(String(32), nullable=False)
    last_name: str = Column(String(64), nullable=True)
    username: str = Column(String(64), nullable=True)
    created: _dt = Column(DateTime, server_default=func.now())
    modified: _dt = Column(DateTime, server_onupdate=FetchedValue(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"TelegramUser(telegram_id={self.telegram_id}, user_id={self.user_id}, first_name={self.first_name})"


class SharedMessage(Base):
    """
    Model representing a shared message between multiple unique Telegram chats
    """

    __tablename__ = "shared_messages"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    share_type: str = Column(String(32), nullable=False)
    share_id: int = Column(BigInteger, nullable=False)
    chat_id: int = Column(BigInteger, nullable=False)
    message_id: int = Column(BigInteger, nullable=False)
    created: _dt = Column(DateTime, server_default=func.now())
    modified: _dt = Column(DateTime, server_onupdate=FetchedValue(), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"SharedMessage(id={self.id}, share_type={self.share_type}, share_id={self.share_id})"


class RegistrationProcess(Base):
    """
    Model representing the sign-up & registration process of the bot
    """

    __tablename__ = "registration_processes"

    telegram_id: int = Column(BigInteger, nullable=False, primary_key=True, unique=True, autoincrement=True)
    application_id: int = Column(BigInteger, nullable=False)
    selected_username: str = Column(String(255), nullable=True)
    core_user_id: int = Column(BigInteger, nullable=True)
    created: _dt = Column(DateTime, server_default=func.now())
    modified: _dt = Column(DateTime, server_onupdate=FetchedValue(), server_default=func.now(), onupdate=func.now())
