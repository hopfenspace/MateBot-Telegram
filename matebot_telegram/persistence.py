"""
MateBot telegram persistence library
"""

import sys
from typing import Optional
from datetime import datetime as _dt

from sqlalchemy import create_engine, Column, DateTime, FetchedValue, Integer, String
from sqlalchemy.engine import Engine as _Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.sql import func


DEFAULT_DATABASE_URL: str = "sqlite:///db.sqlite3"
PRINT_SQLITE_WARNING: bool = True

Base = declarative_base()
_engine: Optional[_Engine] = None
_make_session: Optional[sessionmaker] = None


def init(database_url: str, echo: bool = True, create_all: bool = True):
    """
    Initialize the database bindings

    This function should be called at a very early program stage, before
    any part of it tries to access the database. If this isn't done,
    a temporary database will be used instead, which may be useful for
    debugging, too. See the ``DEFAULT_DATABASE_URL`` constant for details
    about the default connection. Without initialization prior to database
    usage, a warning will be emitted once to prevent future errors.

    :param database_url: the full URL to connect to the database
    :param echo: whether all SQLAlchemy magic should print to screen
    :param create_all: whether the metadata of the declarative base should
        be used to create all non-existing tables in the database
    """

    global _engine, _make_session
    if database_url.startswith("sqlite:"):
        if ":memory:" in database_url or database_url == "sqlite://":
            print(
                "Using the in-memory sqlite3 may lead to later problems. "
                "It's therefore recommended to create a persistent file.",
                file=sys.stderr
            )

        _engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False}
        )
        if PRINT_SQLITE_WARNING:
            print(
                "Using a sqlite database is supported for development and testing environments "
                "only. You should use a production-grade database server for deployment.",
                file=sys.stderr
            )

    else:
        _engine = create_engine(
            database_url,
            echo=echo
        )

    if create_all:
        Base.metadata.create_all(bind=_engine)

    _make_session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine() -> _Engine:
    if _engine is None:
        init(DEFAULT_DATABASE_URL)
    return _engine


def get_new_session() -> Session:
    if _make_session is None or _engine is None:
        init(DEFAULT_DATABASE_URL)
    return _make_session()


class TelegramUser(Base):
    """
    Model representing one end-user alias bind to a MateBot user
    """

    __tablename__ = "telegram_users"

    telegram_id: int = Column(Integer, nullable=False, primary_key=True, unique=True)
    user_id: int = Column(Integer, nullable=False, unique=True)
    first_name: str = Column(String(2048), nullable=False)
    last_name: str = Column(String(2048), nullable=True)
    username: str = Column(String(2048), nullable=True)
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
    share_type: str = Column(String(255), nullable=False)
    share_id: int = Column(Integer, nullable=False)
    chat_id: int = Column(Integer, nullable=False)
    message_id: int = Column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"SharedMessage(id={self.id}, share_type={self.share_type}, share_id={self.share_id})"


class RegistrationProcess(Base):
    """
    Model representing the sign-up & registration process of the bot
    """

    __tablename__ = "registration_processes"

    telegram_id: int = Column(Integer, nullable=False, primary_key=True, unique=True)
    application_id: int = Column(Integer, nullable=False)
    selected_username: str = Column(String(255), nullable=True)
    core_user_id: int = Column(Integer, nullable=True)
