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

def sync_cli(filename):
    config = Config()
    fileconfig = config[filename]

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    print(sync.status)

    sync.sync()

@csvsync_cli.command("pull")
@click.argument("filename")

def pull_cli(filename):
    config = Config()
    fileconfig = config[filename]

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    sync.pull()

@csvsync_cli.command("push")
@click.argument("filename")

def pull_cli(filename):
    config = Config()
    fileconfig = config[filename]

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    sync.push()

@csvsync_cli.command("abort")
@click.argument("filename")

def abort_cli(filename):
    config = Config()
    fileconfig = config[filename]

    sync = Sync(fileconfig, None)

    sync.abort()

if __name__ == "__main__":
    csvsync_cli()
