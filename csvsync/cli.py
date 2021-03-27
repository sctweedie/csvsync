# Main CLI handling for the csvsync command.

from . import config, gsheet, sync, lib
from .config import Config
from .sync import Sync
from .lib import *

import click
import sys
import shutil
import logging

def find_config(config, filename):
    try:
        return config[filename]
    except KeyError:
        eprint("Cannot find config matching filename:", filename)
        exit(1)

@click.group()
@click.option("-d", "--debug", is_flag = True, default = False)

def csvsync_cli(debug):
    if debug:
        logging.basicConfig(filename = "DEBUG.log", level = logging.DEBUG)

    pass

@csvsync_cli.command("pull")
@click.argument("filename")

def cli_pull(filename):
    config = Config()
    fileconfig = find_config(config, filename)

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    sync.cli_pull()

@csvsync_cli.command("push")
@click.argument("filename")

def cli_push(filename):
    config = Config()
    fileconfig = find_config(config, filename)

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    sync.cli_push()

@csvsync_cli.command("abort")
@click.argument("filename")

def cli_abort(filename):
    config = Config()
    fileconfig = find_config(config, filename)

    sync = Sync(fileconfig, None)

    sync.cli_abort()

@csvsync_cli.command("status")
@click.argument("filename")

def cli_status(filename):
    config = Config()
    fileconfig = find_config(config, filename)

    sync = Sync(fileconfig, None)

    sync.cli_status()

if __name__ == "__main__":
    csvsync_cli()
