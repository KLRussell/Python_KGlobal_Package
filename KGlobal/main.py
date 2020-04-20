from getopt import GetoptError, getopt
import sys
import os
import logging

logger = logging.getLogger(__name__)


def main():
    args = sys.argv[1:]

    try:
        opts, args = getopt(args, 'hc', ['help', 'create_master_salt'])
    except GetoptError as exc:
        sys.stderr.write("ERROR: %s" % exc)
        sys.stderr.write(os.linesep)
        sys.exit(1)

    for cmd, arg in opts:
        if cmd == '--help' or cmd == '-h':
            print('KGlobal [-c, --create_master_salt]')
        elif cmd == '--create_master_salt' or cmd == '-c':
            try:
                print('Creating Master Salt Key....')
                from . import create_master_salt_key
                create_master_salt_key()
                print('Master Salt Key has been successfully created')
            except Exception as exc:
                sys.stderr.write("ERROR: %s" % exc)
                sys.stderr.write(os.linesep)
                sys.exit(1)
