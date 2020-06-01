from getopt import GetoptError, getopt
import sys
import os
import logging

logger = logging.getLogger(__name__)


def main():
    args = sys.argv[1:]

    try:
        opts, args = getopt(args, 'hc', ['help', 'create_pepper'])
    except GetoptError as exc:
        sys.stderr.write("ERROR: %s" % exc)
        sys.stderr.write(os.linesep)
        sys.exit(1)

    for cmd, arg in opts:
        if cmd == '--help' or cmd == '-h':
            print('KGlobal [-c, --create_pepper] <Out Filepath (optional)>')
        elif cmd == '--create_pepper' or cmd == '-c':
            try:
                if len(arg) == 1:
                    fp = arg[0]
                else:
                    fp = None

                print('Creating Pepper Key....')
                from . import create_pepper
                create_pepper(fp)
                print('Pepper Key has been successfully created')
            except Exception as exc:
                sys.stderr.write("ERROR: %s" % exc)
                sys.stderr.write(os.linesep)
                sys.exit(1)
