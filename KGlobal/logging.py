from __future__ import unicode_literals

from datetime import datetime

import os
import logging


class LogHandle(object):
    __file_dir = None
    __base_name = None

    """
    Logging that becomes easier and more uniformed
    """

    def __init__(self, file_dir=None, base_name=None):
        """
        Logging settings not forgotten!

        :param file_dir: File directory of where log files will be saved
        :param base_name: A base filename that log files will be saved as
        """

        self.file_dir = file_dir
        self.base_name = base_name

    @property
    def file_dir(self):
        return self.__file_dir

    @file_dir.setter
    def file_dir(self, file_dir):
        if not isinstance(file_dir, (str, type(None))):
            raise Exception("'file_dir' is missing")
        if file_dir and not os.path.exists(file_dir):
            raise Exception("'file_dir' does not exist")

        self.__file_dir = file_dir

    @property
    def base_name(self):
        return self.__base_name

    @base_name.setter
    def base_name(self, base_name):
        if not isinstance(base_name, (str, type(None))):
            raise Exception("'base_name' is missing")

        self.__base_name = base_name

    @staticmethod
    def __clean_handlers():
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

    def write_to_log(self, message, action='info'):
        """
        Logging becomes more organized!

        :param message: Message that you would like to write to log
        :param action: What kind of action would you like the entry to be marked as?
            (debug, info, warning, error, critical)
        """
        if not message:
            raise Exception("'message' is missing")

        self.__clean_handlers()
        filepath = os.path.join(self.__file_dir,
                                "{0}_{1}_Log.txt".format(datetime.now().__format__("%Y%m%d"), self.__base_name))

        logging.basicConfig(filename=filepath,
                            level=logging.DEBUG, format=' %(asctime)s - %(levelname)s - %(message)s')

        print('{0} - {1} - {2}'.format(datetime.now(), action.upper(), message))

        if action.lower() == 'debug':
            logging.debug(message)
        elif action.lower() == 'info':
            logging.info(message)
        elif action.lower() == 'warning':
            logging.warning(message)
        elif action.lower() == 'error':
            logging.error(message)
        elif action.lower() == 'critical':
            logging.critical(message)

    def __del__(self):
        logging.shutdown()
