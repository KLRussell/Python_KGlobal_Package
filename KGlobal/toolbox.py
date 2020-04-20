from __future__ import unicode_literals

import os
from .sql import SQLQueue
from .logging import LogHandle
from exchangelib import Credentials as Exch_Cred, Configuration, DELEGATE

import pathlib as pl


class Toolbox(SQLQueue, LogHandle):
    """
    A toolbox instance class that combines SQLQueue class, LogHandle class, and other various tools for use
    """

    SQL_POOLSIZE = 10
    __local_config = None
    __main_config = None
    __pointer = None

    def __init__(self, script_path, logging_path=None, logging_base_name=None, max_pool_size=SQL_POOLSIZE):
        """
        Lets setup SQLQueue, Logging, Main Config, and Local Config

        :param script_path: Script/Application filepath (ie __file__)
        :param logging_path: (Optional) Filepath to place logging files
        :param max_pool_size: (Optional) SQL max poolsize for connection queue
        """

        if logging_path and os.path.exists(logging_path) and os.path.isdir(logging_path):
            file_dir = logging_path

            if logging_base_name:
                base_name = os.path.basename(logging_base_name)
            else:
                base_name = os.path.basename(script_path)
        else:
            file_dir = None
            base_name = None

        SQLQueue.__init__(self, pool_size=max_pool_size)
        LogHandle.__init__(self, file_dir=file_dir, base_name=base_name)

        from . import master_salt_filepath
        from .data import DataConfig

        if not isinstance(script_path, str):
            raise ValueError("'script_path' %r is not a String" % script_path)

        self.__base_dir = os.path.dirname(script_path)

        if not os.path.exists(self.__base_dir):
            raise ValueError("'script_path' %r does not exist as directory" % self.__base_dir)
        if not os.path.basename(script_path):
            raise ValueError("'script_path' %r is a directory and not a filepath" % script_path)

        ptr_paths = list(pl.Path(self.__base_dir).glob('*.ptr'))

        if ptr_paths:
            self.__base_name = os.path.splitext(os.path.basename(ptr_paths[0]))[0]
        else:
            self.__base_name = os.path.splitext(os.path.basename(script_path))[0]

        if not self.__base_name:
            raise ValueError("'script_path' %r doesn't have a proper file name" % os.path.basename(script_path))

        script_path = os.path.join(self.__base_dir, '%s.ptr' % self.__base_name)

        if os.path.exists(script_path):
            self.pointer = DataConfig(file_dir=self.__base_dir, file_name_prefix=self.__base_name, file_ext='ptr',
                                      salt_key_fp=master_salt_filepath(), new_salt_key=False, encrypt=True)
        else:
            self.__new_pointer()

    @property
    def main_config(self):
        """
        :return: Returns Main Configuration, which is a DataConfig instance class
        """

        return self.__main_config

    @property
    def local_config(self):
        """
        :return: Returns Local Configuration, which is a DataConfig instance class
        """

        return self.__local_config

    @property
    def pointer(self):
        """
        :return: Returns Pointer file, which is a DataConfig instance class
        """

        return self.__pointer

    @pointer.setter
    def pointer(self, pointer):
        from .data import DataConfig, CryptHandle
        if not isinstance(pointer, (DataConfig, type(None))):
            raise ValueError("'pointer' %r is not an instance of DataConfig" % pointer)

        if pointer:
            old_key_path = None
            old_mdb_path = None

            if 'Key_Path' in pointer.keys():
                if not isinstance(pointer['Key_Path'], CryptHandle):
                    del pointer['Key_Path']
                elif not os.path.exists(pointer['Key_Path'].decrypt()):
                    old_key_path = pointer['Key_Path'].decrypt()
                    del pointer['Key_Path']

            if 'Main_DB_Path' in pointer.keys() and not isinstance(pointer['Main_DB_Path'], CryptHandle):
                old_mdb_path = pointer['Main_DB_Path']
                del pointer['Main_DB_Path']

            if 'Local_DB_Path' in pointer.keys() and not isinstance(pointer['Local_DB_Path'], CryptHandle):
                del pointer['Local_DB_Path']

                if 'Key_Path' in pointer.keys() and 'Main_DB_Path' in pointer.keys():
                    lpath = os.path.join(self.__base_dir, '%s.db' % self.__base_name)
                    pointer['Local_DB_Path'].setcrypt(key=pointer['Key_Path'], val=lpath)

            if 'Key_Path' in pointer.keys() and 'Main_DB_Path' in pointer.keys() and 'Local_DB_Path' in pointer.keys():
                self.__pointer = pointer
                self.__set_config()
            else:
                self.__new_pointer(pointer, old_key_path, old_mdb_path)
        else:
            self.__pointer = pointer

    def config_sql_conn(self, sql_config):
        """
        Create a custom SQL connection and add engine to SQL queue pool

        :param sql_config: SQLConfig class instance that can be customizable
        :return: SQL Engine (Engine is still in queue pool)
        """

        engine = self.__find_engine(sql_config)

        if engine is None:
            self.create_sql_engine_to_pool(sql_config=sql_config)
            engine = self.__find_engine(sql_config)

        return engine

    def default_sql_conn(self):
        """
        Creates the default SQL connection and add engine to SQL queue pool

        :return: SQL Engine (Engine is still in queue pool)
        """

        def sql_server_check(mc):
            from . import SQLServerGUI
            from .data import DataConfig

            if not isinstance(mc, DataConfig):
                raise ValueError("'main_config' %r is not an instance of DataConfig" % mc)

            if 'SQL_Server' not in mc.keys() or 'SQL_Database' not in mc.keys():
                s = SQLServerGUI()

                if not s.server.decrypt() or not s.database.decrypt():
                    return False

                mc['SQL_Server'] = s.server
                mc['SQL_Database'] = s.database
                mc.sync()

            return True

        if sql_server_check(self.main_config):
            from .sql import SQLConfig

            sql_config = SQLConfig(server=self.main_config['SQL_Server'].decrypt(),
                                   database=self.main_config['SQL_Database'].decrypt())

            engine = self.__find_engine(sql_config)

            if engine is None:
                self.create_sql_engine_to_pool(sql_config=sql_config)
                engine = self.__find_engine(sql_config)

            return engine

    def default_exchange_conn(self):
        """
        Create default Exchangelib e-mail connection

        :return: Returns Exchange instance class, which is a child class of Exchangelib's Account instance class
        """
        def email_check(mc):
            from . import EmailGUI
            from .data import DataConfig

            if not isinstance(mc, DataConfig):
                raise ValueError("'main_config' %r is not an instance of DataConfig" % mc)

            if 'Exchange_Server' not in mc.keys() or 'Exchange_Email' not in mc.keys():
                s = EmailGUI()

                if not s.server.decrypt() or not s.email_addr.decrypt():
                    return False

                mc['Exchange_Server'] = s.server
                mc['Exchange_Email'] = s.email_addr
                mc.sync()

            return True

        def cred_check(mc):
            from . import CredentialsGUI
            from .data import DataConfig

            if not isinstance(mc, DataConfig):
                raise ValueError("'main_config' %r is not an instance of DataConfig" % mc)

            if 'Exchange_Cred' not in mc.keys():
                s = CredentialsGUI()

                if not s.credentials.username.decrypt() or not s.credentials.password.decrypt():
                    return False

                mc['Exchange_Cred'] = s.credentials
                mc.sync()

            return True

        from .exchangelib import Exchange

        if email_check(self.main_config) and cred_check(self.main_config):
            cred = Exch_Cred(self.main_config['Exchange_Cred'].username.decrypt(),
                             self.main_config['Exchange_Cred'].password.decrypt())
            config = Configuration(server=self.main_config['Exchange_Server'].decrypt(), credentials=cred)
            return Exchange(primary_smtp_address=self.main_config['Exchange_Email'].decrypt(), config=config,
                            autodiscover=False, access_type=DELEGATE)

    def __find_engine(self, config):
        from .sql import SQLConfig, SQLEngineClass

        if not isinstance(config, SQLConfig):
            raise ValueError("'config' %r is not an instance of SQLConfig" % config)

        for engine in self.pool_list:
            if isinstance(engine, SQLEngineClass) and engine.sql_config == config:
                return engine

    def __new_pointer(self, pointer=None, old_key_path=None, old_db_path=None):
        from .setup_gui import SetupGUI

        obj = SetupGUI(local_db_dir=self.__base_dir, pointer=pointer, salt_key_path=old_key_path,
                       main_db_path=old_db_path)

        if obj.pointer:
            self.pointer = obj.pointer

    def __set_config(self):
        if self.__pointer:
            from .data import DataConfig

            key = self.__pointer['Key_Path']
            main_db = self.__pointer['Main_DB_Path']
            local_db = self.__pointer['Local_DB_Path']

            local_file_name_prefix = os.path.splitext(os.path.basename(local_db.decrypt()))
            main_file_name_prefix = os.path.splitext(os.path.basename(main_db.decrypt()))
            self.__local_config = DataConfig(file_dir=os.path.dirname(local_db.decrypt()),
                                             file_name_prefix=local_file_name_prefix[0],
                                             file_ext=local_file_name_prefix[1].replace('.', ''),
                                             salt_key_fp=key.decrypt(), new_salt_key=False, encrypt=True)
            self.__main_config = DataConfig(file_dir=os.path.dirname(main_db.decrypt()),
                                            file_name_prefix=main_file_name_prefix[0],
                                            file_ext=main_file_name_prefix[1].replace('.', ''),
                                            salt_key_fp=key.decrypt(), new_salt_key=False, encrypt=True)

    def __del__(self):
        SQLQueue.__del__(self)
        LogHandle.__del__(self)
