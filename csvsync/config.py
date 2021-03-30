import configparser
import os
import logging

class Config:
    def __init__(self):
        config = configparser.ConfigParser(
            defaults = {'token': 'token.pickle',
                        'credentials': 'credentials.json',
                        'syncdir': 'csvsync',
                        'quote': 'minimal',
                        'pad_lines': True,
                        'debug': False})
        self.config = config

        config.read([os.path.expanduser('~/.csvsync.ini')])

        path = "."
        self.basepath = path

        while True:
            file = os.path.join(path, 'csvsync.ini')
            if os.path.exists(file):
                self.basepath = path
                logging.debug("Using base path %s and ini file at %s" % (path, file))
                config.read([file])
                break

            parent = os.path.normpath(os.path.join("..", path))
            if os.path.samefile(path, parent):
                break
            path = parent

    def save(self):
        with open('csvsync.ini', 'wt') as file:
            self.config.write(file)

    def __getitem__(self, filename):
        for section_name in self.config:
            if section_name == 'DEFAULT':
                continue

            section = self.config[section_name]

            if section_name == filename:
                logging.debug("Found config section " + section_name)
                return FileConfig(self, section, section_name)

            section_filename = section.get('filename', None)
            if section_filename and self._matches(section_filename, filename):
                logging.debug("Found config section " + section_name)
                return FileConfig(self, section, section_name)

        raise KeyError

    def _matches(self, config_filename, user_filename):
        """
        Checks if a supplied user filename matches the filename stored in a
        config section
        """
        canonical_config_filename = os.path.abspath(os.path.join(self.basepath, config_filename))
        canonical_user_filename = os.path.abspath(user_filename)
        return canonical_user_filename == canonical_config_filename

    def file_relative_to_config(self, filename):
        fullpath = os.path.join(self.basepath, filename)
        return os.path.normpath(fullpath)

class FileConfig:
    def __init__(self, config, section, section_name):
        self.config = config
        self.section = section
        self.section_name = section_name

    def expand_config_filename(self, key):

        filename = self.section[key]

        # When looking up config files, if the filename has no dirname
        # component, we default to the local csvsync subdir

        if os.path.dirname(filename) == '':
            subdir = self.config.file_relative_to_config(self.section['syncdir'])
            filename = os.path.join(subdir, filename)

        filename = os.path.expanduser(filename)

        return filename

    def __getitem__(self, key):
        return self.section[key]

    def __contains__(self, key):
        return key in self.section

