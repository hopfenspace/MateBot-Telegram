"""
MateBot telegram config loader
"""

import os as _os
from typing import List, Optional

import pydantic as _pydantic

try:
    import ujson as _json  # noqa
except ImportError:
    import json as _json


class Configuration(_pydantic.BaseModel):
    class CurrencyConfiguration(_pydantic.BaseModel):
        digits: _pydantic.NonNegativeInt
        factor: _pydantic.PositiveInt
        symbol: _pydantic.constr(min_length=1, max_length=4)

    class CallbackConfiguration(_pydantic.BaseModel):
        enabled: bool
        public_url: _pydantic.AnyHttpUrl
        address: str
        port: _pydantic.conint(gt=1, lt=65536)
        shared_secret: Optional[_pydantic.constr(max_length=2047)]

    class AutoForwardConfiguration(_pydantic.BaseModel):
        communism: List[int]
        poll: List[int]
        refund: List[int]

    class ChatConfiguration(_pydantic.BaseModel):
        transactions: List[int]
        notification: List[int]
        debugging: List[int]

    application: _pydantic.constr(max_length=255)
    password: _pydantic.constr(max_length=255)
    database_url: str
    database_debug: bool
    server: _pydantic.AnyHttpUrl
    ssl_verify: bool
    ca_path: Optional[str]
    user_agent: Optional[str]
    token: str
    workers: _pydantic.PositiveInt
    currency: CurrencyConfiguration
    callback: CallbackConfiguration
    auto_forward: AutoForwardConfiguration
    chats: ChatConfiguration
    logging: dict


def setup_configuration(*paths: str) -> Configuration:
    for path in paths:
        if _os.path.exists(path):
            with open(path) as f:
                return Configuration(**_json.load(f))
    raise RuntimeError("No configuration file found.")
