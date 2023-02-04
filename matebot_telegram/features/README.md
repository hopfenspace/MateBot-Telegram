# MateBot Telegram features package

This package provides implementations for various features
of the MateBot Telegram bot. Look into a package or module to
find all functionality for that specific feature grouped
together. Some exceptions from this structure exist:

The `api_callbacks` package stores explicit API callback handlers
which are not related to other bot functionality, so that they can
be found in one place. If callbacks directly relate to a feature,
they can be found in the respective subpackage (e.g. the
`POLL_CREATED` handler is in the `poll.api_callback` module)

The structure of a subpackage follows the following template:

1. `__init__.py` imports the most important implementations
   of the modules in the package
2. `command.py` provides the Telegram command(s)
3. `callback_query.py` provides the Telegram callback query(s)
4. `inline.py` provides the Telegram inline query(s)
5. `message.py` provides the Telegram message handler(s)
6. `api_callback.py` provides functions/coroutines used as
   callbacks when receiving push events from the API server
7. `common.py` provides functionality for the other modules in the
    package, even though the symbols there are not to be exported
