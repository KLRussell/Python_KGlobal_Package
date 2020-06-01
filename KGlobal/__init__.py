from __future__ import unicode_literals

from .credentials import Credentials
from .xml import XML
from .exchangelib import ExchangeToMsg
from .toolbox import Toolbox
from .setup_gui import CredentialsGUI, EmailGUI, SQLServerGUI

import os
import pkg_resources

__package_name__ = 'KGlobal'
__author__ = 'Kevin Russell'
__version__ = "1.3.0"
__description__ = '''File, encryption, SQL, XML, and etc...'''
__url__ = 'https://github.com/KLRussell/Python_KGlobal_Package'

__all__ = [
    "Toolbox",
    "Credentials",
    "ExchangeToMsg",
    "XML",
    "CredentialsGUI",
    "EmailGUI",
    "SQLServerGUI",
    "default_pepper_filepath",
    "create_pepper"
]


def default_pepper_filepath():
    if isinstance(__path__, list):
        path = __path__[0]
    else:
        path = __path__

    dir_path = os.path.join(path, 'Pepper')
    return os.path.join(dir_path, 'Pepper.key')


def create_pepper(filepath=None):
    from .data.create_pepper import create_pepper

    if filepath and os.path.exists(os.path.dirname(filepath)):
        if not os.path.isfile(filepath):
            raise ValueError("'filepath' is not a file")
        if os.path.splitext(filepath) != '.key':
            raise ValueError("'filepath' is not a .key extension!")

        pepper_fp = filepath
    else:
        pepper_fp = default_pepper_filepath()

    create_pepper(os.path.dirname(pepper_fp), os.path.basename(pepper_fp))
