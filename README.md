# MateBot Telegram

Telegram Bot as frontend to the [MateBot API](https://github.com/CrsiX/MateBot)
that allows users to buy Mate, ice cream and pizza or more, easily share bills
or get refunds from the community when they paid for something used by everyone.

**This bot currently works without using the aforementioned API, since it's not
ready to be used yet. The bot will be updated to use it as soon as possible.**

## Installation

### Requirements

- Python >= 3.7.3
- [python-telegram-bot](https://pypi.org/project/python-telegram-bot/)
- [tzlocal](https://pypi.org/project/tzlocal/)
- [pymysql](https://pypi.org/project/PyMySQL/)

You may have [mysqlclient](https://pypi.org/project/mysqlclient/) installed
on your machine. In case it's available, we prefer it over
[pymysql](https://pypi.org/project/PyMySQL/). However, it requires installation
of OS-specific libraries which the pure-Python implementation does not.
Therefore, there's the requirement for the pure-Python library while
the other one could be used too.

## Documentation

See docs folder or [our deployed documentation](https://docs.hopfenspace.org/matebot)

## License

See [license](LICENSE)
