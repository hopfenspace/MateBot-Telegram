"""
PTB's persistence implementation using SQLAlchemy
"""

from typing import Dict, Optional

import telegram.ext
from telegram.ext._utils.types import BD, CD, CDCData, ConversationDict, ConversationKey, UD


class BotPersistence(telegram.ext.BasePersistence):
    async def get_user_data(self) -> Dict[int, UD]:
        print("get_user_data")
        return {}

    async def update_user_data(self, user_id: int, data: UD) -> None:
        print("update_user_data", user_id, "/", data)

    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        print("refresh_user_data", user_id, user_data)

    async def drop_user_data(self, user_id: int) -> None:
        print("drop_user_data", user_id)

    async def get_callback_data(self) -> Optional[CDCData]:
        print("get_callback_data")
        return None

    async def update_callback_data(self, data: CDCData) -> None:
        print("update_callback_data", data)

    async def flush(self) -> None:
        print("flush")

    # Below are the features that are not required and therefore not implemented

    async def get_bot_data(self) -> BD:
        pass

    async def update_bot_data(self, data: BD) -> None:
        pass

    async def refresh_bot_data(self, bot_data: BD) -> None:
        pass

    async def get_chat_data(self) -> Dict[int, CD]:
        pass

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        pass

    async def get_conversations(self, name: str) -> ConversationDict:
        pass

    async def update_conversation(self, name: str, key: ConversationKey, new_state: Optional[object]) -> None:
        pass
