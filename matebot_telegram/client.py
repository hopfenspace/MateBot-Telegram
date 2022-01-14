"""
MateBot SDK client to be used across the project
"""

import logging

from matebot_sdk.exceptions import APIConnectionException
from matebot_sdk.schemas.sdk import ClientConfig
from matebot_sdk.sdk import AsyncSDK

from .config import config
from .util import get_event_loop

SDK = AsyncSDK(
    base_url=config["server"],
    app_name=config["application"],
    password=config["password"],
    ca_path=config["ca-path"],
    configuration=ClientConfig(
        adjust_stock=config["adjust-stock"],
        respect_stock=config["respect-stock"]
    ),
    logger=logging.getLogger("sdk.client")
)

try:
    get_event_loop().run_until_complete(SDK.setup())
except APIConnectionException as exc:
    raise ImportError(f"Unable to connect to API server at {config['server']}") from exc
