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
    class CallbackConfiguration(_pydantic.BaseModel):
        enabled: bool
        public_url: _pydantic.AnyHttpUrl
        address: str
        port: int
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
    server: _pydantic.AnyHttpUrl
    ca_path: Optional[str]
    token: str
    callback: CallbackConfiguration
    auto_forward: AutoForwardConfiguration
    chats: ChatConfiguration
    logging: dict


config: Configuration

for path in ["config.json", _os.path.join("..", "config.json")]:
    if _os.path.exists(path):
        with open(path) as f:
            config = Configuration(**_json.load(f))
        break
else:
    raise ImportError("No configuration file found")
