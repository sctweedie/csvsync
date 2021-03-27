# Main CLI handling for the csvsync command.

from . import config, gsheet, sync, lib
from .config import Config
from .state import Sync
from .lib import *

import click
import sys
import os
import shutil
import logging

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

    sync = Sync(fileconfig)

    sync.cli_pull()

@csvsync_cli.command("push")
@click.argument("filename")

def cli_push(filename):
    config = Config()
    fileconfig = find_config(config, filename)

    sync = Sync(fileconfig)

    sync.cli_push()

@csvsync_cli.command("abort")
@click.argument("filename")

def cli_abort(filename):
    config = Config()
    fileconfig = find_config(config, filename)

    sync = Sync(fileconfig)

    status = sync.status

    if status != 'MERGING':
        eprint('Error: no sync in progress (status is %s)' % status)
        exit(1)

    if os.path.exists(sync.download_filename):
        os.unlink(sync.download_filename)

    if os.path.exists(sync.merge_filename):
        os.unlink(sync.merge_filename)

    sync.status = 'READY'


@csvsync_cli.command("status")
@click.argument("filename")

def cli_status(filename):
    config = Config()
    fileconfig = find_config(config, filename)

    sync = Sync(fileconfig)

    status = sync.status

    print(status)

    # Status will also dump additional file stats to the DEBUG log, if enabled:
    logging.debug("File info:")
    for attr, desc in [("local_filename", "Local file"),
                       ("status_filename", "status"),
                       ("download_filename", "download"),
                       ("merge_filename", "merge"),
                       ("save_filename", "saved (LCA)")]:
        filename = getattr(sync, attr)
        present = "(Present)" if os.path.exists(filename) else "(Not present)"
        logging.debug("  %s: %s %s" % (desc, filename, present))

##
## General support code for CLI handlers
##

def find_config(config, filename):
    try:
        return config[filename]
    except KeyError:
        eprint("Cannot find config matching filename:", filename)
        exit(1)

def cli_check_ready(config, fileconfig):
    pass

class CLIError(Exception):
    """Exception class for general sync CLI errors"""

    def __init__(self, message, *args):
        progname = os.path.basename(sys.argv[0])
        self.message = f"{progname}: {message}"

        super(CLIError, self).__init__(message, *args)

##
## Top-level entrypoint.
##
## Sets up exception handlers then falls straight into click CLI handling.
##

def cli_entrypoint():
    try:
        csvsync_cli()
    except CLIError as e:
        eprint(e.message)
        sys.exit(1)

if __name__ == "__main__":
    cli_entrypoint()
