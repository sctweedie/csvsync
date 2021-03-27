import sys
import os

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class CLIError(Exception):
    """Exception class for general sync CLI errors"""

    def __init__(self, message, *args, level = "Error"):
        progname = os.path.basename(sys.argv[0])
        self.message = f"{progname}: {level} - {message}"

        super(CLIError, self).__init__(message, *args)

