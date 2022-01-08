"""
MateBot telegram shared message library
"""

import os
import threading
from typing import Dict, List, Optional, Union

try:
    import ujson as json
except ImportError:
    import json

from config import config


class SharedMessage:
    def __init__(self, share_type: str, share_id: int, chat_id: int, message_id: int):
        self.share_type = share_type
        self.share_id = share_id
        self.chat_id = chat_id
        self.message_id = message_id

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return vars(self) == vars(other)

    def to_json(self) -> Dict[str, Union[int, str]]:
        return {
            "share_type": self.share_type,
            "share_id": self.share_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id
        }


class SharedMessageHandler:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._lock = threading.Lock()
        if not os.path.exists(self.storage_path):
            with self._lock:
                with open(self.storage_path, "w") as f:
                    f.write("[]")

    def get_all_messages(self) -> List[SharedMessage]:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
        return [SharedMessage(**entry) for entry in content]

    def get_messages_of(self, share_type: str, share_id: Optional[int] = None) -> List[SharedMessage]:
        filtered_msgs = [shared_msg for shared_msg in self.get_all_messages() if shared_msg.share_type == share_type]
        if share_id is None:
            return filtered_msgs
        return [shared_msg for shared_msg in filtered_msgs if shared_msg.share_id == share_id]

    def add_message(self, shared_message: SharedMessage) -> bool:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
            content.append(shared_message.to_json())
            with open(self.storage_path, "w") as f:
                json.dump(content, f)
        return True

    def add_message_by(self, share_type: str, share_id: int, chat_id: int, message_id: int) -> bool:
        return self.add_message(SharedMessage(share_type, share_id, chat_id, message_id))

    def delete_message(self, shared_message: SharedMessage) -> bool:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
            old_length = len(content)
            shared_messages = [msg for msg in [SharedMessage(**entry) for entry in content] if msg != shared_message]
            new_length = len(shared_messages)
            with open(self.storage_path, "w") as f:
                json.dump(content, f)
        return old_length > new_length

    def delete_message_by(self, share_type: str, share_id: int, chat_id: int, message_id: int) -> bool:
        return self.delete_message(SharedMessage(share_type, share_id, chat_id, message_id))


shared_message_handler = SharedMessageHandler(config["bot-storage"])
