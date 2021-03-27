import click
import csvsync
import os

from csvsync.cli import csvsync_cli
from csvsync.config import Config
from csvsync.sync import Sync
from csvsync import gsheet

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

    fileconfig = csvsync.cli.find_config(config, filename)

    auth = gsheet.Auth(fileconfig)
    sheet = gsheet.Sheet(fileconfig, auth)

    sync = Sync(fileconfig, sheet)

    print(sync.status)

    do_sync(sync, continue_sync)

def do_sync(sync, continue_sync):

    if continue_sync:
        return sync.cli_sync_continue()

    # Test things look OK before we start downloading data.

    # Make sure we have a latest-common-ancestor to work with

    if not os.path.exists(sync.save_filename):
        eprint('Error: no saved copy (%s) exists for file' % sync.save_filename)
        exit(1)

    # Check that the user has specified a primary key for the sync

    try:
        merge_key = sync.fileconfig['key']
    except KeyError:
        eprint('Error: no primary key defined for file')
        exit(1)

    # Make sure we're not already in the middle of a sync
    # (eg. manually resolving a sync with conflicts)

    sync.state_change("READY", "MERGING")

    sync.download()

    try:
        # Create a 3-way merge
        result = sync.merge_files()

        if not result:
            eprint("Warning: merge conflicts in %s" % sync.local_filename)
            eprint("Fix conflicts then continue with csvsync sync --continue $file")
            exit(1)

        sync.merge_complete()

    finally:
        sync.cleanup_download()

def do_sync_continue(sync):
    sync.merge_complete()

