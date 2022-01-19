"""
MateBot SDK client to be used across the project
"""

import asyncio
import logging

from matebot_sdk.exceptions import APIConnectionException
from matebot_sdk.schemas.sdk import ClientConfig
from matebot_sdk.sdk import AsyncSDK

from . import util
from .config import config


logger = logging.getLogger("client")

SDK = AsyncSDK(
    base_url=config["server"],
    app_name=config["application"],
    password=config["password"],
    ca_path=config["ca-path"],
    configuration=ClientConfig(
        adjust_stock=config["adjust-stock"],
        respect_stock=config["respect-stock"]
    ),
    callback=(config["callback"]["public-url"], config["callback"]["username"], config["callback"]["password"]),
    logger=logging.getLogger("sdk.client")
)


def setup_sdk() -> bool:
    logger.debug("Setting up SDK client...")
    if util.event_loop is None:
        logger.error("Event loop uninitialized! Refusing to setup SDK client!")
        return False
    try:
        fut = asyncio.run_coroutine_threadsafe(SDK.setup(), loop=util.event_loop)
        fut.result()
        # get_event_loop().run_until_complete(SDK.setup())
    except APIConnectionException as exc:
        raise ImportError(f"Unable to connect to API server at {config['server']}") from exc
    return True
