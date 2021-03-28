# Core state handling for all sync operations.
#
# Contains the common Sync class representing the current operation; includes
# the main state machine support, plus various file upload/download utility
# functions.

from . import gsheet, config
from .lib import *

import os
import configparser
import shutil
import filecmp
import logging

import csvdiff3

class Sync:

    def __init__(self, fileconfig):
        self.fileconfig = fileconfig

        # Perform some basic tests on the file config being used here.
        # We will propagate exceptions cleanly up to the CLI entry
        # point before getting too deep into the actual work.

        self.check_config_key('filename')
        self.check_config_key('spreadsheet_id')
        self.check_config_key('sheet')
        self.check_config_key('key')

        self.__gsheet = None

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

    def check_config_key(self, keyname):
        fileconfig = self.fileconfig
        if keyname not in fileconfig:
            raise CLIError("Incomplete config, "
                           f"""required key "{keyname}" missing """
                           f"for file {fileconfig.section_name}")

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
        old = self.__status

        try:
            self.__status, self.__command = value
            logging.debug(f"State {old} -> {self.__status}, command := {self.__command}")

        except ValueError:
            self.__status = value
            logging.debug(f"State {old} -> {self.__status}")

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

        if command:
            if command == "none":
                assert new == "READY"
            else:
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

    def copy_file(self, file1, file2):
        filename1 = getattr(self, file1 + "_filename")
        filename2 = getattr(self, file2 + "_filename")
        logging.debug(f"Copying file {filename1} to {filename2}")
        shutil.copy(filename1, filename2)

    @property
    def gsheet(self):
        if not self.__gsheet:
            auth = gsheet.Auth(self.fileconfig)
            self.__gsheet = gsheet.Sheet(self.fileconfig, auth)

        return self.__gsheet

