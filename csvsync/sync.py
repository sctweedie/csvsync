from . import gsheet, config
from .lib import eprint

import os
import configparser
import shutil
import filecmp
import logging

import csvdiff3

class OldSync:

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

