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

    if continue_sync:
        return do_sync_continue(sync)

    # Test things look OK before we start downloading data.  The
    # initial setup of the Sync class will have done basic validation
    # of the config, but now we need to test that the various files we
    # need are actually present etc.

    # Make sure we have a latest-common-ancestor to work with

    if not os.path.exists(sync.save_filename):
        eprint('Error: no saved copy (%s) exists for file' % sync.save_filename)
        exit(1)

    # Make sure we're not already in the middle of a sync
    # (eg. manually resolving a sync with conflicts)

    csvsync.cli.cli_check_state(sync)

    sync.state_change("READY", "PULL", command = "sync")

    # Prepare files for merge:
    # Download the remote file, and take a copy of the local file

    sync.download()
    sync.copy_file("local", "local_copy")

    sync.state_change("PULL", "MERGE")

    # Create a 3-way merge
    result = merge_files(sync)

    sync.state_change("MERGE", "RESOLVE")

    sync.copy_file("merge", "local")

    if not result:
        logging.debug("Conflicts found in merge")

        eprint(f"Warning: merge conflicts in {sync.local_filename}\n"
               f"Fix conflicts then continue with\n"
               f"  $ csvsync sync --continue {sync.fileconfig.section_name}")
        exit(1)

    logging.debug("No conflicts found in merge")
    merge_complete(sync)

def do_sync_continue(sync):
    merge_complete(sync)

def merge_files(sync):
    # Locate the 3 files for a 3-way merge:
    #
    # LCA (Latest Common Ancestor) is the local SAVE file

    filename_LCA = sync.save_filename

    # Branch A is the csvsync copy of the local working file

    filename_A = sync.local_copy_filename

    # Branch B is the downloaded copy of the remote google sheet

    filename_B = sync.download_filename

    # And our output is going to be the local MERGE file

    filename_output = sync.merge_filename

    # We need to lookup the right primary key for the merge

    merge_key = sync.fileconfig['key']
    quote = sync.fileconfig['quote']

    eprint("Merging files...")
    logging.debug("Running 3-way merge: "
                  f"{filename_LCA}, {filename_A}, {filename_B} -> {filename_output}")
    with open(filename_LCA, 'rt') as file_LCA:
        with open(filename_A, 'rt') as file_A:
            with open(filename_B, 'rt') as file_B:
                with open(filename_output, 'wt') as file_output:
                    result = csvdiff3.merge3.merge3(file_LCA, file_A, file_B,
                                                    merge_key,
                                                    quote = quote,
                                                    output = file_output)

    logging.debug(f"Merge completed with result {result}")
    # We return True (success) if the merge did NOT have a conflict
    return not result

def merge_complete(sync):
    sync.state_change("RESOLVE", "PUSH")

    # The 3-way merge has been completed (either automatically, or
    # after manual conflict resolution).
    #
    # We can now save it as a SAVE file as LCA for the next 3-way
    # merge, and upload the results.

    sync.copy_file("local", "save")

    # If the download file still exists (ie. we didn't pause for a
    # manual conflict resolution), and the reconciled file is the
    # same as the download, then we don't need to re-upload.

    if os.path.exists(sync.download_filename) and \
       filecmp.cmp(sync.download_filename, sync.save_filename,
                   shallow = False):
        eprint('No changes pending against remote file, skipping re-upload')
    else:
        sync.upload()

    sync.state_change("PUSH", "READY", command = "none")
