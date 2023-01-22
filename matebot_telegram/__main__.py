#!/usr/bin/env python3

import sys
import argparse

from matebot_telegram import config, entrypoint


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json", help="path to the configuration file")
    return parser


if __name__ == "__main__":
    args = get_parser().parse_args()
    if args.config:
        config.setup_configuration(args.config)
    if not hasattr(config, "config"):
        print("Failed to read configuration file. Make sure a config file exists and is readable.", file=sys.stderr)
        exit(1)
    exit(entrypoint.main(config.config))
