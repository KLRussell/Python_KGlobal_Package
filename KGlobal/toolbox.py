from __future__ import unicode_literals

import os
from .sql import SQLQueue
from .logging import LogHandle
from exchangelib import Credentials as Exch_Cred, Configuration, DELEGATE
from exchangelib.errors import UnauthorizedError, TransportError
from traceback import format_exc

import pathlib as pl


class TBoxBase(object):
    """
    A toolbox instance class that combines SQLQueue class, LogHandle class, and other various tools for use
    """

    __local_config = None
    __main_config = None
    __pointer = None

    def __init__(self, script_path):
        """
        Lets setup SQLQueue, Logging, Main Config, and Local Config

        :param script_path: Script/Application filepath (ie __file__)
        """

        from . import default_key_dir
        from .setup_gui import DefaultKeySetupGUI
        from .data import DataConfig

        self.__base_dir = os.path.dirname(script_path)
        key_dir = default_key_dir()
        key_ptr_fp = os.path.join(key_dir, "Key.dir")
        salt_key_fp = os.path.join(key_dir, "Salt.key")
        pepper_key_fp = os.path.join(key_dir, "Pepper.key")

        if not (os.path.exists(salt_key_fp) and os.path.exists(pepper_key_fp)) and not os.path.exists(key_ptr_fp):
            obj = DefaultKeySetupGUI(self.__base_dir)

            if not obj.key_generated:
                raise ValueError("Unable to establish toolbox because key creation wasn't established")

        if not isinstance(script_path, str):
            raise ValueError("'script_path' %r is not a String" % script_path)
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
                                      encrypt=True)
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
    def local_config_dir(self):
        """
        :return: Returns Local Configuration directory, which is a great place to setup folders and script input/output
        """

        if self.__pointer and 'Local_DB_Path' in self.__pointer.keys():
            return os.path.dirname(self.__pointer['Local_DB_Path'].decrypt())

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
            old_mdb_path = None

            if 'Main_DB_Path' in pointer.keys() and not isinstance(pointer['Main_DB_Path'], CryptHandle):
                old_mdb_path = pointer['Main_DB_Path']
                del pointer['Main_DB_Path']

            if 'Local_DB_Path' in pointer.keys() and not isinstance(pointer['Local_DB_Path'], CryptHandle):
                del pointer['Local_DB_Path']

                if 'Main_DB_Path' in pointer.keys():
                    lpath = os.path.join(self.__base_dir, 'Local_Settings.db')
                    pointer['Local_DB_Path'].setcrypt(key='Local_DB_Path', val=lpath)

            if 'Main_DB_Path' in pointer.keys() and 'Local_DB_Path' in pointer.keys():
                self.__pointer = pointer
                self.__set_config()
            else:
                self.__new_pointer(pointer, old_mdb_path)
        else:
            self.__pointer = pointer

    def __new_pointer(self, pointer=None, old_db_path=None):
        from .setup_gui import MainDatabaseGUI

        obj = MainDatabaseGUI(local_db_dir=self.__base_dir, pointer=pointer, main_db_path=old_db_path)

        if obj.pointer:
            self.pointer = obj.pointer

    def __set_config(self):
        if self.__pointer:
            from .data import DataConfig

            main_db = self.__pointer['Main_DB_Path']
            local_db = self.__pointer['Local_DB_Path']

            local_file_name_prefix = os.path.splitext(os.path.basename(local_db.decrypt()))
            main_file_name_prefix = os.path.splitext(os.path.basename(main_db.decrypt()))
            self.__local_config = DataConfig(file_dir=os.path.dirname(local_db.decrypt()),
                                             file_name_prefix=local_file_name_prefix[0],
                                             file_ext=local_file_name_prefix[1].replace('.', ''), encrypt=True)
            self.__main_config = DataConfig(file_dir=os.path.dirname(main_db.decrypt()),
                                            file_name_prefix=main_file_name_prefix[0],
                                            file_ext=main_file_name_prefix[1].replace('.', ''), encrypt=True)


class Toolbox(TBoxBase, SQLQueue, LogHandle):
    DEFAULT_CONNECTION_SIZE = 10

    def __init__(self, script_path, logging_dir=None, logging_folder=None, logging_base_name=None, max_pool_size=None,
                 *args, **kwargs):
        TBoxBase.__init__(self, script_path=script_path)
        SQLQueue.__init__(self, max_pool_size=max_pool_size)
        LogHandle.__init__(self)

        file_dir = None
        base_name = None

        if logging_dir and os.path.exists(logging_dir) and os.path.isdir(logging_dir):
            file_dir = logging_dir
        elif self.local_config_dir and logging_folder:
            file_dir = os.path.join(self.local_config_dir, logging_folder)

        if file_dir:
            if logging_base_name:
                base_name = os.path.basename(logging_base_name)
            else:
                base_name = os.path.basename(script_path)

            self.file_dir = file_dir
            self.base_name = base_name

    def config_sql_conn(self, sql_config, new_instance=False, conn_max_pool_size=DEFAULT_CONNECTION_SIZE):
        """
        Create a custom SQL connection and add engine to SQL queue pool

        :param sql_config: SQLConfig class instance that can be customizable
        :param new_instance: Creates a new instance of default sql connection (Default False)
        :param conn_max_pool_size: Maximum of sql connections (Optional)
        :return: SQL Engine (Engine is still in queue pool)
        """

        if new_instance:
            engine = None
        else:
            engine = self.__find_engine(sql_config)

        if engine is None:
            engine = self.create_sql_engine_to_pool(sql_config=sql_config, conn_max_pool_size=conn_max_pool_size)

        return engine

    def default_sql_conn(self, new_instance=False, conn_max_pool_size=DEFAULT_CONNECTION_SIZE):
        """
        Creates the default SQL connection and add engine to SQL queue pool

        :param new_instance: Creates a new instance of default sql connection (Default False)
        :param conn_max_pool_size: Maximum of sql connections (Optional)
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

        def redo_settings(mc):
            from . import SQLServerGUI
            s = SQLServerGUI(server=mc['SQL_Server'].decrypt(), database=mc['SQL_Database'].decrypt())

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

            if new_instance:
                engine = None
            else:
                engine = self.__find_engine(sql_config)

            if engine is None:
                engine = self.create_sql_engine_to_pool(sql_config=sql_config, conn_max_pool_size=conn_max_pool_size)

                if not engine and redo_settings(self.main_config):
                    return self.default_sql_conn()

            return engine

    def default_exchange_conn(self, user_name=None, user_pass=None, auto_renew=False):
        """
        Create default Exchangelib e-mail connection

        :return: Returns Exchange instance class, which is a child class of Exchangelib's Account instance class
        """
        def email_check(mc, un, up):
            from . import EmailGUI
            from .data import DataConfig
            from .data import CryptHandle

            if un and up:
                if not isinstance(un, CryptHandle):
                    raise ValueError("'user_name' %r is not an instance of CryptHandle" % un)
                if not isinstance(up, CryptHandle):
                    raise ValueError("'user_pass' %r is not an instance of CryptHandle" % up)

                return True
            elif mc:
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

        def email_change(mc):
            from . import EmailGUI

            s = EmailGUI(server=mc['Exchange_Server'].decrypt(), email_addr=mc['Exchange_Email'].decrypt())

            if not s.server.decrypt() or not s.email_addr.decrypt():
                return False

            mc['Exchange_Server'] = s.server
            mc['Exchange_Email'] = s.email_addr
            mc.sync()

            return True

        def cred_check(mc, un, up):
            from . import CredentialsGUI
            from .data import DataConfig

            if un and up:
                if not un.decrypt():
                    raise ValueError("'user_name' is an empty CryptHandle object")
                elif not up.decrypt():
                    raise ValueError("'user_pass' is an empty CryptHandle object")

                return [un, up]
            elif mc:
                if not isinstance(mc, DataConfig):
                    raise ValueError("'main_config' %r is not an instance of DataConfig" % mc)

                if 'Exchange_Cred' not in mc.keys():
                    s = CredentialsGUI()

                    if not s.credentials.username.decrypt():
                        raise ValueError("'user_name' is an empty CryptHandle object")
                    elif not s.credentials.password.decrypt():
                        raise ValueError("'user_pass' is an empty CryptHandle object")

                    mc['Exchange_Cred'] = s.credentials
                    mc.sync()

                return [mc['Exchange_Cred'].username, mc['Exchange_Cred'].password]
            else:
                return [None, None]

        def cred_change(mc, un, up):
            from . import CredentialsGUI

            s = CredentialsGUI(cred=mc['Exchange_Cred'])

            if not s.credentials.username.decrypt():
                raise ValueError("'user_name' is an empty CryptHandle object")
            elif not s.credentials.password.decrypt():
                raise ValueError("'user_pass' is an empty CryptHandle object")

            if un and up:
                return [True, s.credentials.username, s.credentials.password]
            elif mc:
                mc['Exchange_Cred'] = s.credentials
                mc.sync()
                return [True, None, None]
            else:
                return [False, None, None]

        from .exchangelib import Exchange

        if email_check(self.main_config, user_name, user_pass):
            uname, upass = cred_check(self.main_config, user_name, user_pass)

            if uname and upass:
                try:
                    cred = Exch_Cred(uname.decrypt(), upass.decrypt())
                    config = Configuration(server=self.main_config['Exchange_Server'].decrypt(), credentials=cred)
                    return Exchange(primary_smtp_address=self.main_config['Exchange_Email'].decrypt(), config=config,
                                    autodiscover=False, access_type=DELEGATE, auto_renew=auto_renew)
                except UnauthorizedError as e:
                    self.write_to_log(format_exc())
                    self.write_to_log("Error Code {0}, {1}".format(type(e).__name__, str(e)))
                    cred_chg, uname, upass = cred_change(self.main_config, user_name, user_pass)

                    if cred_chg:
                        self.default_exchange_conn(user_name=uname, user_pass=upass, auto_renew=auto_renew)

                except (ValueError, TransportError) as e:
                    self.write_to_log(format_exc())
                    self.write_to_log("Error Code {0}, {1}".format(type(e).__name__, str(e)))

                    if email_change(self.main_config):
                        self.default_exchange_conn(user_name=user_name, user_pass=user_pass, auto_renew=auto_renew)
                except Exception as e:
                    self.write_to_log(format_exc())
                    self.write_to_log("Error Code {0}, {1}".format(type(e).__name__, str(e)))

    def __find_engine(self, config):
        from .sql import SQLConfig, SQLEngineClass

        if not isinstance(config, SQLConfig):
            raise ValueError("'config' %r is not an instance of SQLConfig" % config)

        for engine in self.pool_list:
            if isinstance(engine, SQLEngineClass) and engine.sql_config == config:
                return engine

    def __del__(self):
        SQLQueue.__del__(self)
        LogHandle.__del__(self)
