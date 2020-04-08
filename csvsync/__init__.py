#!/usr/bin/python3

from . import config, gsheet, sync, lib
from .config import Config
from .sync import Sync

import click
import sys
import shutil

@click.group()
def csvsync_cli():
    pass

@csvsync_cli.command("sync")
@click.argument("filename")

def cli_sync(filename):
    config = Config()
    fileconfig = config[filename]

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    print(sync.status)

    sync.cli_sync()

@csvsync_cli.command("pull")
@click.argument("filename")

def cli_pull(filename):
    config = Config()
    fileconfig = config[filename]

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    sync.cli_pull()

@csvsync_cli.command("push")
@click.argument("filename")

def cli_push(filename):
    config = Config()
    fileconfig = config[filename]

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    sync.cli_push()

@csvsync_cli.command("abort")
@click.argument("filename")

def cli_abort(filename):
    config = Config()
    fileconfig = config[filename]

    sync = Sync(fileconfig, None)

    sync.cli_abort()

@csvsync_cli.command("status")
@click.argument("filename")

def cli_status(filename):
    config = Config()
    fileconfig = config[filename]

    sync = Sync(fileconfig, None)

    sync.cli_status()

if __name__ == "__main__":
    csvsync_cli()
