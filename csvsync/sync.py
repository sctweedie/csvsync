from . import gsheet, config
from .lib import eprint

import os
import configparser
import shutil
import filecmp

import csvdiff3

class Sync:
    def __init__(self, fileconfig, gsheet):
        self.fileconfig = fileconfig
        self.gsheet = gsheet

        self.subdir = fileconfig['syncdir']

        basename = os.path.basename(fileconfig['filename'])

        # We will maintain persistent state for the 3-way sync in
        # various files in the csvsync/ subdir:
        #

        # An overall status file (to allow us to detect if there is
        # eg. a pending conflict resolution in progress)
        self.status_filename = os.path.join(self.subdir, basename + '.STATUS')

        # Temporary local download file for the google sheet
        self.download_filename = os.path.join(self.subdir, basename + '.DOWNLOAD')

        # Output of the 3-way merge
        self.merge_filename = os.path.join(self.subdir, basename + '.MERGE')

        # Saved copy of the most recently known Latest Common Ancestor
        # (ie. latest successful merge)
        self.save_filename = os.path.join(self.subdir, basename + '.SAVE')

        self.status_config = configparser.ConfigParser()

        if os.path.exists(self.status_filename):
            self.status_config.read(self.status_filename)

    @property
    def status(self):
        try:
            status = self.status_config['csvsync']['status']
        except KeyError:
            status = None

        self.__status = status
        return status

    @status.setter
    def status(self, value):
        self.__status = value

        try:
            section = self.status_config['csvsync']
        except KeyError:
            self.status_config.add_section('csvsync')
            section = self.status_config['csvsync']

        section['status'] = value
        with open(self.status_filename, 'wt') as configfile:
            self.status_config.write(configfile)

    def download(self):
        filename = self.download_filename
        assert not os.path.exists(filename)

        pad_lines = self.fileconfig['pad_lines']
        eprint("Downloading...")
        self.gsheet.save_to_csv(filename)

    def cleanup_download(self):
        filename = self.download_filename

        os.unlink(filename)

    def upload(self):
        filename = self.save_filename
        assert os.path.exists(filename)

        eprint("Uploading result...")
        self.gsheet.load_from_csv(filename)

    def sync(self):
        status = self.status

        # Test things look OK before we start downloading data.

        # First make sure we're not already in the middle of a sync
        # (eg. manually resolving a sync with conflicts)

        if status != None and status != 'READY':
            eprint('Error: sync already in progress (status is %s)' % status)
            exit(1)

        # Make sure we have a latest-common-ancestor to work with

        if not os.path.exists(self.save_filename):
            eprint('Error: no saved copy (%s) exists for file' % self.save_filename)
            exit(1)

        # Check that the user has specified a primary key for the sync

        try:
            merge_key = self.fileconfig['key']
        except KeyError:
            eprint('Error: no primary key defined for file')
            exit(1)

        self.download()

        try:
            # Create a 3-way merge
            result = self.merge_files()

            if result:
                self.merge_complete()

        finally:
            self.cleanup_download()

    def pull(self):
        status = self.status

        if status != None and status != 'READY':
            eprint('Error: sync already in progress (status is %s)' % status)
            exit(1)

        if os.path.exists(self.save_filename):
            eprint('Error: saved copy (%s) already exists for file' % self.save_filename)
            exit(1)

        self.download()
        os.rename(self.download_filename, self.save_filename)
        shutil.copy(self.save_filename, self.fileconfig['filename'])

    def push(self):
        status = self.status

        if status != None and status != 'READY':
            eprint('Error: sync already in progress (status is %s)' % status)
            exit(1)

        filename = self.fileconfig['filename']

        if not os.path.exists(filename):
            eprint('Error: local file (%s) not found' % filename)
            exit(1)

        shutil.copy(filename, self.save_filename)

        self.upload()

    def abort(self):
        status = self.status

        if status != 'MERGING':
            eprint('Error: no sync in progress (status is %s)' % status)
            exit(1)

        if os.path.exists(self.download_filename):
            os.unlink(self.download_filename)

        if os.path.exists(self.merge_filename):
            os.unlink(self.merge_filename)

        self.status = 'READY'

    def merge_files(self):
        self.status = "MERGING"

        # Locate the 3 files for a 3-way merge:
        #
        # LCA (Latest Common Ancestor) is the local SAVE file

        filename_LCA = self.save_filename

        # Branch A is the local working copy of the file

        filename_A = self.fileconfig['filename']

        # Branch B is the downloaded copy of the remote google sheet

        filename_B = self.download_filename

        # And our output is going to be the local MERGE file

        filename_output = self.merge_filename

        # We need to lookup the right primary key for the merge

        merge_key = self.fileconfig['key']

        eprint("Merging files...")
        with open(filename_LCA, 'rt') as file_LCA:
            with open(filename_A, 'rt') as file_A:
                with open(filename_B, 'rt') as file_B:
                    with open(filename_output, 'wt') as file_output:
                        result = csvdiff3.merge3.merge3(file_LCA, file_A, file_B,
                                                        merge_key,
                                                        output = file_output)

        # We return True (success) if the merge did NOT have a conflict
        return not result

    def merge_complete(self):
        status = self.status

        if status != 'MERGING':
            eprint('Error: merge not in progress (status is %s)' % status)
            exit(1)

        # The 3-way merge has been completed (either automatically, or
        # after manual conflict resolution).
        #
        # We can now save it as a SAVE file as LCA for the next 3-way
        # merge, and upload the results.

        os.rename(self.merge_filename, self.save_filename)
        shutil.copy(self.save_filename, self.fileconfig['filename'])

        # If the download file still exists (ie. we didn't pause for a
        # manual conflict resolution), and the reconciled file is the
        # same as the download, then we don't need to re-upload.

        if os.path.exists(self.download_filename) and \
           filecmp.cmp(self.download_filename, self.save_filename,
                       shallow = False):
            eprint('No changes pending against remote file, skipping re-upload')
        else:
            self.upload()

        self.status = 'READY'
