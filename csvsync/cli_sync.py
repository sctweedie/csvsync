import click
import csvsync
import os
import shutil
import filecmp
import logging

from csvsync.cli import csvsync_cli
from csvsync.config import Config
from csvsync.state import Sync
from csvsync import gsheet
from csvsync.lib import *

import csvdiff3

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

    sync = Sync(fileconfig)

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
        result = merge_files(sync)

        if not result:
            eprint("Warning: merge conflicts in %s" % sync.local_filename)
            eprint("Fix conflicts then continue with csvsync sync --continue $file")
            exit(1)

        merge_complete(sync)

    finally:
        sync.cleanup_download()

def do_sync_continue(sync):
    merge_complete(sync)

def merge_files(sync):
    # Locate the 3 files for a 3-way merge:
    #
    # LCA (Latest Common Ancestor) is the local SAVE file

    filename_LCA = sync.save_filename

    # Branch A is the local working copy of the file

    filename_A = sync.local_filename

    # Branch B is the downloaded copy of the remote google sheet

    filename_B = sync.download_filename

    # And our output is going to be the local MERGE file

    filename_output = sync.merge_filename

    # We need to lookup the right primary key for the merge

    merge_key = sync.fileconfig['key']
    quote = sync.fileconfig['quote']

    eprint("Merging files...")
    with open(filename_LCA, 'rt') as file_LCA:
        with open(filename_A, 'rt') as file_A:
            with open(filename_B, 'rt') as file_B:
                with open(filename_output, 'wt') as file_output:
                    result = csvdiff3.merge3.merge3(file_LCA, file_A, file_B,
                                                    merge_key,
                                                    quote = quote,
                                                    output = file_output)

    # We return True (success) if the merge did NOT have a conflict
    return not result

def merge_complete(sync):
    sync.state_change("MERGING", "POST-PUSH")

    # The 3-way merge has been completed (either automatically, or
    # after manual conflict resolution).
    #
    # We can now save it as a SAVE file as LCA for the next 3-way
    # merge, and upload the results.

    os.rename(sync.merge_filename, sync.save_filename)
    shutil.copy(sync.save_filename, sync.local_filename)

    # If the download file still exists (ie. we didn't pause for a
    # manual conflict resolution), and the reconciled file is the
    # same as the download, then we don't need to re-upload.

    if os.path.exists(sync.download_filename) and \
       filecmp.cmp(sync.download_filename, sync.save_filename,
                   shallow = False):
        eprint('No changes pending against remote file, skipping re-upload')
    else:
        sync.upload()

    sync.state_change("POST-PUSH", "READY")
