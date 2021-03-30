import click
import csvsync
import os
import logging
import filecmp

from csvsync.cli import csvsync_cli
from csvsync.config import Config
from csvsync.state import Sync
from csvsync import gsheet
from csvsync.lib import *

@csvsync_cli.command("pull")
@click.argument("filename")
@click.option("-f", "--force", is_flag = True, default = False)

def cli_pull(filename, force):
    config = Config()
    fileconfig = csvsync.cli.find_config(config, filename)

    sync = Sync(fileconfig)

    # Check we don't already have a command in progress
    csvsync.cli.cli_check_state(sync)

    # Check if we would be overwriting any important local files

    check_already_exists(sync, force)

    sync.state_change("READY", "PULL", command = "pull")

    sync.download()

    # The downloaded file becomes both the local file and the most
    # recent ancestor.

    os.rename(sync.download_filename, sync.ancestor_filename)
    sync.copy_file("ancestor", "local")

    sync.state_change("PULL", "READY", command = "none")

def check_already_exists(sync, force):

    # If the file does not exist locally already, then the pull is fine.

    if not os.path.exists(sync.local_filename):
        logging.debug("PULL: no local file to overwrite, pull is OK")
        return

    # If it exists, we need to see if it has any local modifications
    # (ie. is different from the LCA if present.)

    if os.path.exists(sync.ancestor_filename):
        if filecmp.cmp(sync.local_filename, sync.ancestor_filename):

            # They are the same: we'll save a backup of the local file
            # and allow the pull

            logging.debug("PULL: local file exists but no local changes to overwrite, "
                          "pull is OK")
            do_pull_backup(sync)
            return

        else:

            # Local changes would be overwritten: don't allow the pull
            # unless the user uses --force

            if force:

                logging.debug("PULL: local file changes exist, overwrite forced")
                do_pull_backup(sync)

            else:

                logging.debug("PULL: local file exists and has local changes, pull denied")
                eprint(format_cli_info(f"Pull would overwrite changes to file {sync.local_filename}"))
                eprint(format_cli_info("Use pull --force to override"))
                raise CLIError(f"Overwriting local changes not permitted")

def do_pull_backup(sync):
    eprint(format_cli_info("Local file exists"))
    eprint(format_cli_info(f"Storing backup in {sync.local_copy_filename}"))
    sync.copy_file("local", "local_copy")
    logging.debug(f"PULL: Backup stored in {sync.local_copy_filename}")
