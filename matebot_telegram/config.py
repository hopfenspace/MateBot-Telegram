"""
MateBot telegram config loader
"""

import os as _os
from typing import List, Optional, Union

import pydantic as _pydantic

try:
    import ujson as _json
except ImportError:
    import json as _json


class Configuration(_pydantic.BaseModel):
    class CurrencyConfiguration(_pydantic.BaseModel):
        digits: _pydantic.PositiveInt
        factor: _pydantic.PositiveInt
        symbol: _pydantic.constr(min_length=1, max_length=4)

    class CallbackConfiguration(_pydantic.BaseModel):
        enabled: bool
        public_url: _pydantic.AnyHttpUrl
        address: str
        port: _pydantic.conint(gt=1, lt=65536)
        shared_secret: Optional[_pydantic.constr(max_length=2047)]

    class AutoForwardConfiguration(_pydantic.BaseModel):
        communism: List[Union[str, int]]
        poll: List[Union[str, int]]
        refund: List[Union[str, int]]

    class ChatConfiguration(_pydantic.BaseModel):
        transactions: List[Union[str, int]]
        notification: List[Union[str, int]]
        stacktrace: List[Union[str, int]]
        debugging: List[Union[str, int]]

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


def setup_configuration(*paths: str) -> bool:
    global config
    for path in paths:
        if _os.path.exists(path):
            with open(path) as f:
                config = Configuration(**_json.load(f))
            return True
    return False


config: Configuration  # must be available at runtime, the setup below is just a default

if not setup_configuration("config.json"):
    setup_configuration(_os.path.join("..", "config.json"))
