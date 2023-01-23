# MateBot Telegram

_MateBot Telegram_ is a Telegram Bot as frontend to the
[MateBot API](https://github.com/hopfenspace/MateBot)
that allows users to buy Mate, ice cream and pizza or more, easily
share bills (in the so-called "communisms") or get refunds from the
community when they paid for something used by everyone. It provides
external and internal user relationships with polls about membership
policies as well as the possibility for users to vouch for others.

## Setup

### Installation

1. Make sure you have Python (>= 3.7) and pip (>= 19) installed.
2. Clone this repository recursively, since it requires a submodule.
3. Copy `config.json.sample` to `config.json` and adapt the options at
   the top of the file to fit your needs (you need a running server of
   the MateBot API and maybe also an existing app name and password).
   The `database_url` needs to be recognized by SQLAlchemy. See
   [here](https://docs.sqlalchemy.org/en/20/core/connections.html)
   for details about the URL format.
4. Create and activate a virtual environment for this project:
   `python3 -m venv venv && source venv/bin/activate`
5. Install the requirements of this project:
   `venv/bin/pip3 install -r requirements.txt`

### Execution

`venv/bin/python3 -m matebot_telegram`

Optional: This repository provides a minimal systemd sample file at
`matebot-telegram.service.sample`. Copy this file to `matebot-telegram.service`
and adapt the settings in there to fit your environment. Then create a symlink
from the systemd unit file storage (e.g. `/etc/systemd/system/` on Debian-like
systems) to this file and run `systemctl daemon-reload`. You should now have a
systemd service `matebot-telegram` that can be started and stopped easily.
To enable auto-start at system boot, use `systemctl enable matebot-telegram`.

## License

See [license](LICENSE).
