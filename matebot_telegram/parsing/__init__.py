"""
MateBot library responsible for parsing incoming messages
"""

from .parser import CommandParser
from .util import Namespace

__all__ = [
    "CommandParser",
    "Namespace"
]
