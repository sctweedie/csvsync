import click
import csvsync
import os
import logging

from csvsync.cli import csvsync_cli
from csvsync.config import Config
from csvsync.state import Sync
from csvsync import gsheet
from csvsync.lib import *

@csvsync_cli.command("pull")
@click.argument("filename")

def cli_pull(filename):
    config = Config()
    fileconfig = csvsync.cli.find_config(config, filename)

    sync = Sync(fileconfig)

    # Check we don't already have a command in progress
    csvsync.cli.cli_check_state(sync)

    if os.path.exists(sync.ancestor_filename):
        eprint('Error: saved copy (%s) already exists for file' % sync.ancestor_filename)
        exit(1)

    sync.download()
    os.rename(sync.download_filename, sync.ancestor_filename)
    shutil.copy(sync.ancestor_filename, sync.local_filename)

