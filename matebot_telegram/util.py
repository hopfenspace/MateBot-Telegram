import sys
import enum
import json
import asyncio
import logging
import traceback
from typing import Any, Callable, List, Optional, Union

import requests
import telegram.ext

from . import config, connector, schemas


class PermissionLevel(enum.Enum):
    ANYONE = 0
    ANY_ACTIVE = 1
    ANY_WITH_VOUCHER = 2
    ANY_INTERNAL = 3
    ANY_WITH_PERMISSION = 4
    NOBODY = 5


class FakeTelegramUser:
    def __init__(self, telegram_id: int, name: Optional[str] = None):
        self.id = telegram_id
        self.name = name or "<unknown>"


def get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError(f"Event loop {loop} is closed!")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


def safe_send(bot: telegram.Bot, chat_id: Union[int, str], default: str, fallback: str, *args, **kwargs) -> bool:
    try:
        bot.send_message(chat_id, default, *args, **kwargs)
        return True
    except telegram.error.BadRequest as exc:
        if not str(exc).startswith("Can't parse entities"):
            raise
        logger = kwargs.get("logger") or logging.getLogger(__name__)
        logger.exception(f"Sending {default!r} failed due to entity parsing problems: {exc!s}")
        bot.send_message(chat_id, fallback, *args, **kwargs)
        logger.debug("The message has been sent without formatting enabled (raw text).")
        return False


def safe_call(default: Callable[[], Any], fallback: Callable[[], Any], logger: logging.Logger = None) -> bool:
    try:
        default()
        return True
    except telegram.error.BadRequest as exc:
        if not str(exc).startswith("Can't parse entities"):
            raise
        logger = logger or logging.getLogger(__name__)
        logger.exception(f"Calling sender function {default} failed due to entity parsing problems: {exc!s}")
        fallback()
        logger.debug(f"Calling fallback function {fallback} was successful instead.")
        return False


def extract_alias_from(user: schemas.User) -> Optional[schemas.Alias]:
    aliases = [a for a in user.aliases if a.application == config.config["app"]]
    if len(aliases) == 0:
        return
    return aliases[0]


def ensure_permissions(user: schemas.User, level: PermissionLevel, msg: telegram.Message, operation: str) -> bool:
    """
    Ensure that a user is allowed to perform an operation that requires specific permissions

    .. note::

        This function will automatically reply to the incoming message when
        the necessary permissions are not fulfilled. Use the return value
        to determine whether you should simply quit further execution of
        your method (returned ``False``) or not (returned ``True``).

    :param user: MateBot user that tries to execute a specific command
    :type user: matebot_telegram.schemas.User
    :param level: minimal required permission level to be allowed to perform some action
    :type level: int
    :param msg: incoming message containing the command in question
    :type msg: telegram.Message
    :param operation: name of the operation that was attempted by the user
    :type operation: str
    :return: whether further access should be allowed (``True``) or not (``False``)
    :rtype: bool
    :raises TypeError: when an expected type was violated
    """

    for i, t in [(user, schemas.User), (level, PermissionLevel), (msg, telegram.Message)]:
        if not isinstance(i, t):
            raise TypeError(f"Expected type {t.__name__}, got {type(level)} instead")

    if level.value == 0:
        return True

    if level.value >= 1 and not user.active:
        alias = extract_alias_from(user)
        name = alias.app_username if alias else user.id
        msg.reply_text(f"The user {name!r} is not active. It can't perform {operation!r}.")
        return False

    if level.value >= 2 and user.external and user.voucher is None:
        msg.reply_text(
            f"You can't perform {operation!r}. You are an external user "
            "without voucher. For security purposes, every external user "
            "needs an internal voucher. Use /help for more information."
        )
        return False

    if level.value >= 3 and user.external:
        msg.reply_text(
            f"You can't perform {operation!r}. You are an external user. "
            "To perform this command, you must be marked as internal user "
            "by community approval. Use /help for more information."
        )
        return False

    if level.value >= 4 and not user.permission:
        msg.reply_text(f"You can't perform {operation!r}. You don't have permissions to vote.")
        return False

    if level.value >= 5:
        msg.reply_text(f"Nobody is allowed to perform {operation!r}.")
        return False
    return True


def get_alias_by(obj: Union[telegram.User, FakeTelegramUser], answer: Callable[[str], Any], connect: connector.APIConnector = None) -> Optional[schemas.Alias]:
    connect = connect or connector.connector
    response = connect.get(f"/v1/aliases/application/{connect.app_name}")
    if not response.ok:
        raise RuntimeError  # TODO: implement better exception handling
    hits = [e for e in response.json() if e["app_user_id"] == str(obj.id)]
    if len(hits) == 0:
        return handle_unknown_user(obj, answer)
    return schemas.Alias(**hits[0])


def get_user_by(obj: Union[int, telegram.User, FakeTelegramUser], answer: Callable[[str], Any], connect: connector.APIConnector = None) -> Optional[schemas.User]:
    connect = connect or connector.connector
    if isinstance(obj, int):
        return connect.get(f"/v1/users/{obj}")
    elif isinstance(obj, telegram.User) or isinstance(obj, FakeTelegramUser):
        alias = get_alias_by(obj, answer, connect=connect)
        if alias is None:
            return
        response = connect.get(f"/v1/users/{alias.user_id}")
        if not response.ok:
            return handle_unknown_user(obj, answer)
        return schemas.User(**response.json())
    raise TypeError(f"Unexpected type {type(obj)}")


def get_consumables(connect: connector.APIConnector = None) -> List[schemas.Consumable]:
    connect = connect or connector.connector
    response = connect.get("/v1/consumables")
    if not response.ok:
        logging.getLogger("util").error(f"Failed to fetch consumables. HTTP {response.status_code}.")
        return []
    return [schemas.Consumable(**entry) for entry in response.json()]


def handle_unknown_user(telegram_user: Union[telegram.User, FakeTelegramUser], answer: Callable[[str], Any]):
    answer(
        f"It looks like {telegram_user.name} was not found on the server. "
        "Please write /start to the bot in a private chat to start using it."
    )


def log_error(update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
    """
    Log any error and its traceback to sys.stdout and send it to developers

    :param update: Telegram Update where the error probably occurred
    :type update: telegram.Update
    :param context: context of the error
    :type context: telegram.ext.CallbackContext
    :return: None
    """

    logger = logging.getLogger("error")
    if update is None:
        logger.warning("Error handler called without Update object. Check for network/connection errors!")
        token = config.config["token"]
        response = requests.get(f"https://api.telegram.org/bot{token}/getme")
        if response.status_code != 200:
            logger.error("Network check failed. Telegram API seems to be unreachable.")
        else:
            logger.debug("Network check succeeded. Telegram API seems to be reachable.")

    if not any(sys.exc_info()):
        logger.error("Error handler called without an exception. Stack trace following as debug message...")
        logger.debug("".join(traceback.format_stack()))
        return

    logger.exception("Something raised an unhandled exception, it will be sent to the developers")

    def send_to(env, rcv, text, parse_mode, extra_text=None) -> None:
        try:
            msg = env.bot.send_message(rcv, text, parse_mode=parse_mode)
            if extra_text is not None:
                msg.reply_text(extra_text, parse_mode=parse_mode, quote=True)
        except telegram.TelegramError:
            logger.exception(f"Error while sending logs to {rcv}!")

    for receiver in config.config["chats"]["notification"]:
        send_to(
            context,
            receiver,
            f"Unhandled exception: {sys.exc_info()[1]}",
            None
        )

    for receiver in config.config["chats"]["stacktrace"]:
        send_to(
            context,
            receiver,
            f"```\n{traceback.format_exc()}```",
            "MarkdownV2"
        )

    for receiver in config.config["chats"]["debugging"]:
        extra = "No Update object found."
        if update is not None:
            extra = json.dumps(update.to_dict(), indent=2, sort_keys=True)
        send_to(
            context,
            receiver,
            f"```\n{traceback.format_exc()}```",
            "MarkdownV2",
            f"Extended debug information:\n```\n{extra}```"
        )
