"""
MateBot callback query for invalid callback data, which happens when inline keyboards can't be read or get dropped
"""

import telegram.ext

from ..base import BaseCallbackQuery, ExtendedContext


class InvalidCallbackDataCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for invalid callback data
    """

    def __init__(self):
        super().__init__(
            "",
            telegram.ext.InvalidCallbackData,
            {"": self.handle}
        )

    async def handle(self, update: telegram.Update, context: ExtendedContext, _: str) -> None:
        """
        Handle invalid (i.e., unavailable or outdated) callback data by simply apologizing
        """

        try:
            context.drop_callback_data(update.callback_query)
        except LookupError as exc:
            self.logger.debug(
                f"Callback data for update {update.update_id} / query "
                f"{update.callback_query.id} not found (as expected): {exc}"
            )

        await update.callback_query.answer(
            "Sorry, this feature is not available anymore. The inline keyboard "
            "has already expired. Please try to create a new keyboard.",
            show_alert=True
        )
