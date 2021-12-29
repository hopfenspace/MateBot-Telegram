# MateBot Telegram

Telegram Bot as frontend to the [MateBot API](https://github.com/hopfenspace/MateBot)
that allows users to buy Mate, ice cream and pizza or more, easily share bills
or get refunds from the community when they paid for something used by everyone.

## Setup

### Installation

1. Make sure you have Python (>= 3.7) and pip (>= 19) installed.
2. Clone this repository.
3. Copy `config.json.sample` to `config.json` and adapt the options at
    the top of the file to fit your needs (you need a running server of
    the MateBot API and maybe also an existing app name and password).
4. `python3 -m venv venv`
5. `venv/bin/pip3 install -r requirements.txt`

### Execution

`venv/bin/python3 -m matebot_telegram`

## Documentation

See `docs` folder or [our deployed documentation](https://docs.hopfenspace.org/matebot).

## License

See [license](LICENSE)
