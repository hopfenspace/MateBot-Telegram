# MateBot Telegram features package

This package provides implementations for various features
of the MateBot Telegram bot. Look into a package or module to
find all functionality for that specific feature grouped
together. Some exceptions from this structure exist:

1. The `base` package provides utilities used by the feature 
   implementations (i.e., base classes and re-exported
   features like the extended context type and the error package).
   Note that this package re-exports certain symbols from other
   packages, like the `err` module or the `ExtendedContext`.
2. The `api_callbacks` package stores explicit API callback handlers
   which are not related to other bot functionality, so that they can
   be found in one place. If callback directly relate to a feature,
   they can be found in the respective package (e.g. the
   `POLL_CREATED` handler is in the `poll` package)
3. The `_common` module currently holds shared functionality,
   but is due to be re-worked entirely as well.

The structure of a subpackage follows the following template:

1. `__init__.py` imports the most important implementations
   of the modules in the package
2. `command.py` provides the Telegram command(s)
3. `callback_query.py` provides the Telegram callback query(s)
4. `inline.py` provides the Telegram inline query(s)
5. `api_callback.py` provides functions/coroutines used as
   callbacks when receiving push events from the API server
6. `common.py` provides functionality for the other modules in the
    package, even though the symbols there are not to be exported
