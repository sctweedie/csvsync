#!/usr/bin/python3

from . import config, gsheet, sync, lib
from .config import Config
from .sync import Sync

import click
import sys
import shutil
import logging

def eprint(*args, **kwargs):
    """
    print to stderr
    """
    print (*args, file=sys.stderr, **kwargs)

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

@csvsync_cli.command("sync")
@click.option("-c", "--continue", is_flag = True, default = False)
@click.argument("filename")

def cli_sync(**args):
    config = Config()

    filename = args["filename"]
    # We need to process the args this way to avoid using a named
    # argument "continue" that collides with the Python continue
    # keyword
    continue_sync = args["continue"]

    fileconfig = find_config(config, filename)

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    print(sync.status)

    sync.cli_sync(continue_sync)

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
