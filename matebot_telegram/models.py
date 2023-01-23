"""
MateBot telegram persistence library
"""

from typing import List
from datetime import datetime as _dt

from sqlalchemy import BigInteger, Column, DateTime, FetchedValue, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
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


class CallbackButton(Base):
    """
    Model representing a single button for a inline keyboard markup
    """

    __tablename__ = "callback_buttons"

    id: int = Column(Integer, nullable=False, primary_key=True, unique=True, autoincrement=True)
    button_id: str = Column(String(32), nullable=False, unique=True)
    """Example: '307b2b50d71f47ffa2edd1396e0acb57' or any other UUID string"""
    button_text: str = Column(String(128), nullable=False)
    """Example: 'donate confirm 100 42' or any other callback button string"""
    keyboard_place: int = Column(Integer, nullable=False)
    """Used for ordering of the entries to the keyboard buttons"""
    keyboard_id: int = Column(Integer, ForeignKey("callback_keyboards.id", ondelete="CASCADE"), nullable=False)
    """Reference to the keyboard containing the button"""

    keyboard: "CallbackKeyboard" = relationship("CallbackKeyboard", back_populates="buttons")


class CallbackKeyboard(Base):
    """
    Model representing an inline keyboard markup with attached callback data
    """

    __tablename__ = "callback_keyboards"

    id: int = Column(Integer, nullable=False, primary_key=True, unique=True, autoincrement=True)
    keyboard_id: str = Column(String(32), nullable=False, unique=True)
    """Example: '121f23b5f42e496ca3996ea37296f6c5' or any other UUID string"""
    creation_time: float = Column(Float, nullable=False)

    buttons: List[CallbackButton] = relationship("CallbackButton", back_populates="keyboard", cascade="all,delete")


class CallbackQuery(Base):
    """
    Model representing an active (or recently active) callback query
    """

    __tablename__ = "callback_queries"

    id: int = Column(Integer, nullable=False, primary_key=True, unique=True, autoincrement=True)
    query_id: int = Column(BigInteger, nullable=False)
    keyboard_id: str = Column(String(32), nullable=False)  # no relation to CallbackKeyboard required by application
    """Example: '8e8895b23d1b487e9167f256564b51a2' or any other UUID string"""
