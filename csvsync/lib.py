import sys
import os

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def format_cli_info(message, level = "Info"):
    progname = os.path.basename(sys.argv[0])
    return f"{progname}: {level} - {message}"

class CLIError(Exception):
    """Exception class for general sync CLI errors"""

    def __init__(self, message, *args, level = "Error"):
        progname = os.path.basename(sys.argv[0])
        self.message = format_cli_info(message, level)

        super(CLIError, self).__init__(message, *args)

