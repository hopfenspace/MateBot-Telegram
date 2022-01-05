"""
MateBot SDK client to be used across the project
"""

import logging

from matebot_sdk.schemas import ClientConfig
from matebot_sdk.sdk import AsyncSDK

from .config import config

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
