"""
MateBot command executor classes for /pay (deprecated)
"""

from typing import ClassVar

from .refund import RefundCommand as _RefundCommand


class PayCommand(_RefundCommand):
    """
    Command executor for /pay

    This command is considered deprecated and will only provide an alias for /refund.
    """

    COMMAND_NAME: ClassVar[str] = "pay"

    def __init__(self):
        super().__init__()
        self.description += "\n\nThis command is considered deprecated and will only provide an alias for /refund."
