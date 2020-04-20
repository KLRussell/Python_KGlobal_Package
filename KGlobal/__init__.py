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
__version__ = "1.2.2"
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
    "master_salt_filepath",
    "create_master_salt_key"
]


def master_salt_filepath():
    from .data import create_salt

    if isinstance(__path__, list):
        path = __path__[0]
    else:
        path = __path__

    dir_path = os.path.join(path, 'master_salt')

    return os.path.join(dir_path, 'salt_key.key')


def create_master_salt_key():
    from .data.create_salt import create_salt
    ms_fp = master_salt_filepath()
    create_salt(os.path.dirname(ms_fp), os.path.basename(ms_fp))
