from . import gsheet, config
from .lib import eprint

import os
import configparser
import shutil
import filecmp
import logging

import csvdiff3

class Sync:

    def __init__(self, fileconfig, gsheet):
        self.fileconfig = fileconfig
        self.gsheet = gsheet

        self.subdir = fileconfig.config.file_relative_to_config(fileconfig['syncdir'])
        self.local_filename = fileconfig.config.file_relative_to_config(self.fileconfig['filename'])

        basename = fileconfig.section.get('cachename', os.path.basename(fileconfig['filename']))

        # We will maintain persistent state for the 3-way sync in
        # various files in the csvsync/ subdir:
        #

        # An overall status file (to allow us to detect if there is
        # eg. a pending conflict resolution in progress)
        self.status_filename = os.path.join(self.subdir, basename + '.STATUS')

        # Temporary local download file for the google sheet
        self.download_filename = os.path.join(self.subdir, basename + '.DOWNLOAD')

        # Temporary copy of the local file.
        # For 3-way merge, the local file will be updated with the contents of the merge, for the user
        # to edit in-place for conflict resolution
        # The "local" copy here can be used to undo the merge and restore to the original contents.
        self.local_copy_filename = os.path.join(self.subdir, basename + '.LOCAL')

        # The download and local file copies above are left in place after a merge/resolve
        # completes, and can be considered backups of the old copies of the local and
        # remote contents.

        # Output of the 3-way merge:
        self.merge_filename = os.path.join(self.subdir, basename + '.MERGE')

        # Saved copy of the most recently known Latest Common Ancestor
        # (ie. latest successful merge)
        self.save_filename = os.path.join(self.subdir, basename + '.SAVE')

        self.status_config = configparser.ConfigParser()

        if os.path.exists(self.status_filename):
            self.status_config.read(self.status_filename)

    def __load_status(self):
        try:
            if self.__loaded_status:
                return
        except AttributeError:
            pass

        try:
            status = self.status_config['csvsync']['status']
        except KeyError:
            status = "NEW"

        try:
            command = self.status_config['csvsync']['current_command']
        except KeyError:
            command = "none"

        self.__status = status
        self.__command = command
        self.__loaded_status = True

    @property
    def status(self):
        self.__load_status()
        return self.__status

    @property
    def command(self):
        self.__load_status()
        return self.__command

    @status.setter
    def status(self, value):
        try:
            self.__status, self.__command = value
        except ValueError:
            self.__status = value

        try:
            section = self.status_config['csvsync']
        except KeyError:
            self.status_config.add_section('csvsync')
            section = self.status_config['csvsync']

        section['status'] = self.__status
        section['current_command'] = self.__command
        with open(self.status_filename, 'wt') as configfile:
            self.status_config.write(configfile)

    def state_change(self, old, new, command = None):
        if self.status != old:
            eprint("Error, state is %s, expecting %s.  Aborting." % (self.status, old))
            exit(1)

        logging.debug("State %s -> %s" % (old, new))
        if command:
            assert self.status == "READY"
            self.status = (new, command)
        else:
            self.status = new

    def download(self):
        filename = self.download_filename
        assert not os.path.exists(filename)

        pad_lines = self.fileconfig['pad_lines']
        eprint("Downloading...")
        self.gsheet.save_to_csv(filename, pad_lines)

    def cleanup_download(self):
        filename = self.download_filename

        os.unlink(filename)

    def upload(self):
        filename = self.save_filename
        assert os.path.exists(filename)

        eprint("Uploading result...")
        self.gsheet.load_from_csv(filename)

    def cli_pull(self):
        status = self.status

        if status != None and status != 'READY':
            eprint('Error: sync already in progress (status is %s)' % status)
            exit(1)

        if os.path.exists(self.save_filename):
            eprint('Error: saved copy (%s) already exists for file' % self.save_filename)
            exit(1)

        self.download()
        os.rename(self.download_filename, self.save_filename)
        shutil.copy(self.save_filename, self.local_filename)

    def cli_push(self):
        status = self.status

        if status != None and status != 'READY':
            eprint('Error: sync already in progress (status is %s)' % status)
            exit(1)

        filename = self.local_filename

        if not os.path.exists(filename):
            eprint('Error: local file (%s) not found' % filename)
            exit(1)

        shutil.copy(filename, self.save_filename)

        self.upload()

    def cli_abort(self):
        status = self.status

        if status != 'MERGING':
            eprint('Error: no sync in progress (status is %s)' % status)
            exit(1)

        if os.path.exists(self.download_filename):
            os.unlink(self.download_filename)

        if os.path.exists(self.merge_filename):
            os.unlink(self.merge_filename)

        self.status = 'READY'

    def cli_status(self):
        status = self.status

        print(status)

        # Status will also dump additional file stats to the DEBUG log, if enabled:
        logging.debug("File info:")
        for attr, desc in [("local_filename", "Local file"),
                           ("status_filename", "status"),
                           ("download_filename", "download"),
                           ("merge_filename", "merge"),
                           ("save_filename", "saved (LCA)")]:
            filename = getattr(self, attr)
            present = "(Present)" if os.path.exists(filename) else "(Not present)"
            logging.debug("  %s: %s %s" % (desc, filename, present))

    def merge_files(self):
        # Locate the 3 files for a 3-way merge:
        #
        # LCA (Latest Common Ancestor) is the local SAVE file

        filename_LCA = self.save_filename

        # Branch A is the local working copy of the file

        filename_A = self.local_filename

        # Branch B is the downloaded copy of the remote google sheet

        filename_B = self.download_filename

        # And our output is going to be the local MERGE file

        filename_output = self.merge_filename

        # We need to lookup the right primary key for the merge

        merge_key = self.fileconfig['key']
        quote = self.fileconfig['quote']

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

    def merge_complete(self):
        self.state_change("MERGING", "POST-PUSH")

        # The 3-way merge has been completed (either automatically, or
        # after manual conflict resolution).
        #
        # We can now save it as a SAVE file as LCA for the next 3-way
        # merge, and upload the results.

        os.rename(self.merge_filename, self.save_filename)
        shutil.copy(self.save_filename, self.local_filename)

        # If the download file still exists (ie. we didn't pause for a
        # manual conflict resolution), and the reconciled file is the
        # same as the download, then we don't need to re-upload.

        if os.path.exists(self.download_filename) and \
           filecmp.cmp(self.download_filename, self.save_filename,
                       shallow = False):
            eprint('No changes pending against remote file, skipping re-upload')
        else:
            self.upload()

        self.state_change("POST-PUSH", "READY")
