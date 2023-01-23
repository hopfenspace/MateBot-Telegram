#!/usr/bin/env python3

import os
import sys
import argparse

from matebot_telegram import config, entrypoint


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="path to the configuration file")
    return parser


if __name__ == "__main__":
    args = get_parser().parse_args()
    try:
        if args.config:
            conf = config.setup_configuration(args.config)
        else:
            conf = config.setup_configuration("config.json", os.path.join("matebot_telegram", "config.json"))
    except RuntimeError:
        print("Failed to read configuration file. Make sure a config file exists and is readable.", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(entrypoint.main(conf))
