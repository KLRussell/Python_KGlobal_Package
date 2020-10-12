from getopt import GetoptError, getopt
import sys
import os
import logging

logger = logging.getLogger(__name__)


def main():
    args = sys.argv[1:]

    try:
        opts, args = getopt(args, 'hc', ['help', 'create_keys'])
    except GetoptError as exc:
        sys.stderr.write("ERROR: %s" % exc)
        sys.stderr.write(os.linesep)
        sys.exit(1)

    for cmd, arg in opts:
        if cmd == '--help' or cmd == '-h':
            print('KGlobal [-c, --create_keys] <Out Directory (optional)>')
        elif cmd == '--create_keys' or cmd == '-c':
            try:
                if len(arg) == 1:
                    key_dir = arg[0]
                else:
                    key_dir = None

                if key_dir and not os.path.isdir(key_dir):
                    raise ValueError("Key directory is not a directory")
                if key_dir and not os.path.exists(key_dir):
                    raise ValueError("Key directory does not exist")

                if not key_dir:
                    from . import default_key_dir
                    key_dir = default_key_dir()

                print('Creating Salt & Pepper Keys....')
                from .data import create_key
                create_key(key_dir, "Salt.key")
                create_key(key_dir, "Pepper.key")
                print('Salt & Pepper Keys have been successfully created')
            except Exception as exc:
                sys.stderr.write("ERROR: %s" % exc)
                sys.stderr.write(os.linesep)
                sys.exit(1)
