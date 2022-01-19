"""
MateBot telegram library for storing persistent data in JSON files
"""

import os
import threading
from typing import Dict, List

try:
    import ujson as json  # noqa
except ImportError:
    import json

from .config import config


class BotStorage:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._lock = threading.Lock()
        if not os.path.exists(self.storage_path):
            with self._lock:
                with open(self.storage_path, "w") as f:
                    f.write("{}")

    def get_all(self) -> Dict[str, List[dict]]:
        with self._lock:
            with open(self.storage_path) as f:
                return json.load(f)

    def get(self, key: str) -> List[dict]:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
        return content.get(key, [])

    def contains(self, key: str) -> bool:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
        return key in content

    def contains_obj(self, key: str, obj: dict) -> bool:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
        return key in content and obj in content[key]

    def add(self, key: str, obj: dict) -> bool:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
            if key not in content:
                content[key] = []
            content[key].append(obj)
            with open(self.storage_path, "w") as f:
                json.dump(content, f)
        return True

    def delete(self, key: str, obj: dict) -> bool:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
            if key not in content:
                return False
            old_content = content[key]
            new_content = [d for d in old_content if d != obj]
            content[key] = new_content
            with open(self.storage_path, "w") as f:
                json.dump(content, f)
        return len(old_content) > len(new_content)

    def delete_all(self, key: str) -> bool:
        with self._lock:
            with open(self.storage_path) as f:
                content = json.load(f)
            if key not in content:
                return False
            content.pop(key)
            with open(self.storage_path, "w") as f:
                json.dump(content, f)
        return True


storage = BotStorage(config["bot-storage"])
