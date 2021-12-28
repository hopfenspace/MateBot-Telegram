"""
MateBot telegram config provider
"""

import os as _os
try:
    import ujson as _json
except ImportError:
    import json as _json


config: dict

for path in ["config.json", _os.path.join("..", "config.json")]:
    if _os.path.exists(path):
        with open(path) as f:
            config = _json.load(f)
else:
    raise ImportError("No configuration file found")
