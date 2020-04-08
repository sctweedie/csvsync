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
                        'pad_lines': True})
        self.config = config

        config.read([os.path.expanduser('~/.csvsync.ini')])

        path = os.getcwd()
        while True:
            file = os.path.join(path, 'csvsync.ini')
            if os.path.exists(file):
                logging.debug("Using ini file at " + file)
                config.read([file])
                break

            parent,_ = os.path.split(path)
            if parent == path:
                break
            path = parent

    def save(self):
        with open('csvsync.ini', 'wt') as file:
            self.config.write(file)

    def __getitem__(self, filename):
        for section in self.config:
            if section == 'DEFAULT':
                continue

            if section == filename or self.config[section]['filename'] == filename:
                return FileConfig(self, self.config[section])

        raise KeyError

class FileConfig:
    def __init__(self, config, section):
        self.config = config
        self.section = section

    def expand_config_filename(self, key):

        filename = self.section[key]

        # When looking up config files, if the filename has no dirname
        # component, we default to the local csvsync subdir

        if os.path.dirname(filename) == '':
            subdir = self.section['syncdir']
            filename = os.path.join(subdir, filename)

        filename = os.path.expanduser(filename)

        return filename

    def __getitem__(self, key):
        return self.section[key]

