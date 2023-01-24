"""
Database utilities to interact with SQLAlchemy and the DB models
"""

import sys
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine as _Engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base


DEFAULT_DATABASE_URL: str = "sqlite:///sqlite3.db"
PRINT_SQLITE_WARNING: bool = True

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