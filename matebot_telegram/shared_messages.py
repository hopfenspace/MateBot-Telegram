"""
MateBot telegram shared message library
"""

import threading
from typing import Dict, List, Optional, Union

from . import bot_storage


class SharedMessage:
    def __init__(self, share_type: str, share_id: int, chat_id: int, message_id: int):
        self.share_type = str(share_type)
        self.share_id = int(share_id)
        self.chat_id = int(chat_id)
        self.message_id = int(message_id)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return vars(self) == vars(other)

    def to_dict(self) -> Dict[str, Union[int, str]]:
        return {
            "share_type": self.share_type,
            "share_id": self.share_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id
        }


class SharedMessageHandler(bot_storage.SimpleStorageClient):
    IDENTIFIER = "shared-messages"

    def __init__(self, storage: bot_storage.BotStorage):
        super(SharedMessageHandler, self).__init__(storage)
        self._lock = threading.Lock()

    def get_all_messages(self) -> List[SharedMessage]:
        return [SharedMessage(**msg) for msg in self.get()]

    def get_messages_of(self, share_type: str, share_id: Optional[int] = None) -> List[SharedMessage]:
        filtered_msgs = [shared_msg for shared_msg in self.get_all_messages() if shared_msg.share_type == share_type]
        if share_id is None:
            return filtered_msgs
        return [shared_msg for shared_msg in filtered_msgs if shared_msg.share_id == share_id]

    def add_message(self, shared_message: SharedMessage) -> bool:
        with self._lock:
            return self.add(shared_message.to_dict())

    def add_message_by(self, share_type: str, share_id: int, chat_id: int, message_id: int) -> bool:
        with self._lock:
            return self.add(SharedMessage(share_type, share_id, chat_id, message_id).to_dict())

    def delete_message(self, shared_message: SharedMessage) -> bool:
        with self._lock:
            return self.delete(shared_message.to_dict())

    def delete_message_by(self, share_type: str, share_id: int, chat_id: int, message_id: int) -> bool:
        with self._lock:
            return self.delete(SharedMessage(share_type, share_id, chat_id, message_id).to_dict())

    def delete_messages(self, share_type: str, share_id: int) -> bool:
        with self._lock:
            old_messages = [SharedMessage(**d) for d in self.get()]
            new_messages = [
                msg for msg in old_messages
                if msg.share_type != share_type or msg.share_id != share_id
            ]
            self.delete_all()
            for msg in new_messages:
                self.add(msg.to_dict())
        return len(old_messages) > len(new_messages)


shared_message_handler = SharedMessageHandler(bot_storage.storage)
