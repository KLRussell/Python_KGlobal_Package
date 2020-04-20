from __future__ import unicode_literals

from ..data.picklemixin import PickleMixIn
from urllib.parse import quote_plus

import os


class BaseSQLConfig(object):
    pass


class SQLConfig(BaseSQLConfig, PickleMixIn):
    """
    SQL Configuration for generating/storing SQL connection strings. Only supports Alchemy & PYODBC
    """

    config_type = None
    conn_types = ['alchemy', 'pyodbc']
    config_types = ['sql', 'accdb', 'dsn', 'conn_str']

    def __init__(self, conn_type=None, conn_str=None, server=None, database=None, credentials=None, accdb_fp=None,
                 dsn_name=None):
        """
        Types of possible SQL connections:
            * conn_type & conn_str
            * server & database (credentials is optional)
            * accdb_fp
            * dsn_name

        :param conn_type: (Optional) [alchemy, pyodbc]
        :param conn_str: (Optional) Raw SQL connection string
        :param server: (Optional) Server in string format
        :param database: (Optional) Database in string format
        :param credentials: (Optional) Credentials instance class
        :param accdb_fp: (Optional) Access database filepath
        :param dsn_name: (Optional) DSN name
        """

        self.conn_type = None
        self.server = None
        self.database = None
        self.credentials = None
        self.accdb_fp = None
        self.dsn_name = None
        self.conn_str = None

        if conn_type and conn_str:
            self.conn_str_config(conn_type, conn_str)
        elif server and database:
            self.sql_config(server, database, credentials)
        elif accdb_fp:
            self.accdb_config(accdb_fp)
        elif dsn_name:
            self.dsn_config(dsn_name)

    def sql_config(self, server, database, credentials=None):
        """
        Store elements for SQL connection string generation

        :param server: Server in string format
        :param database: Database in string format
        :param credentials: (Optional) Credentials instance class
        """

        from ..credentials import Credentials

        if not isinstance(server, str):
            raise ValueError("'server' must be a String")
        if not isinstance(database, str):
            raise ValueError("'database' must be a String")
        if not isinstance(credentials, (Credentials, type(None))):
            raise ValueError("'credentials' %r must be a Credentials instance" % credentials)

        self.__slots__ = ("conn_type", "server", "database")
        self.config_type = 'sql'
        self.conn_type = 'alchemy'
        self.server = server
        self.database = database
        self.credentials = credentials
        self.conn_str = None
        self.accdb_fp = None
        self.dsn_name = None

    def accdb_config(self, accdb_fp):
        """
        Store elements for SQL connection string generation

        :param accdb_fp: Access database filepath
        """

        if not isinstance(accdb_fp, str):
            raise ValueError("'accdb_fp' must be a String")
        if not os.path.exists(accdb_fp):
            raise ValueError("'accdb_fp' (%s) filepath does not exist" % accdb_fp)
        if accdb_fp.find('.') < 1:
            raise ValueError("'accdb_fp' (%s) file does not have an extension" % os.path.basename(accdb_fp))

        ext = os.path.splitext(accdb_fp)[1].lower()

        if ext not in ('.accdb', '.mdb'):
            raise ValueError("'accdb_fp' (%s) extension must be either (accdb, mdb)" %
                             os.path.basename(accdb_fp))

        self.__slots__ = ("conn_type", "accdb_fp")
        self.conn_type = 'pyodbc'
        self.config_type = 'accdb'
        self.accdb_fp = accdb_fp
        self.conn_str = None
        self.server = None
        self.database = None
        self.credentials = None
        self.dsn_name = None

    def dsn_config(self, dsn_name):
        """
        Store elements for SQL connection string generation

        :param dsn_name: DSN name
        """
        if not isinstance(dsn_name, str):
            raise ValueError("'dsn_name' must be a String")

        self.__slots__ = ("conn_type", "dsn_name")
        self.conn_type = 'pyodbc'
        self.config_type = 'dsn'
        self.dsn_name = dsn_name
        self.conn_str = None
        self.server = None
        self.database = None
        self.credentials = None
        self.accdb_fp = None

    def conn_str_config(self, conn_type, conn_str):
        """
        Store elements for SQL connection string generation

        :param conn_type: [alchemy, pyodbc]
        :param conn_str: Raw SQL connection string
        """

        if conn_type not in self.conn_types:
            raise ValueError("'conn_type' must be either (%s)" % ', '.join(self.conn_types))
        if not isinstance(conn_str, str):
            raise ValueError("'conn_str' must be a String")

        self.__slots__ = ("conn_type", "conn_str")
        self.config_type = 'conn_str'
        self.conn_type = conn_type
        self.conn_str = conn_str
        self.server = None
        self.database = None
        self.credentials = None
        self.accdb_fp = None
        self.dsn_name = None

    def gen_conn_str(self):
        """
        Generates a connection string for sql, accdb, and dsn connections

        :return: connection string
        """

        if self.config_type == 'sql':
            if self.credentials:
                quote = quote_plus(
                    'DRIVER={};PORT={};SERVER={};DATABASE={};Uid={},Pwd={};Trusted_Connection=yes;'.format(
                        '{SQL Server Native Client 11.0}', '1433', self.server, self.database,
                        self.credentials.username.decrypt(), self.credentials.password.decrypt())
                )
            else:
                quote = quote_plus(
                    'DRIVER={};PORT={};SERVER={};DATABASE={};Trusted_Connection=yes;'.format(
                        '{SQL Server Native Client 11.0}', '1433', self.server, self.database)
                )
            return '{}+pyodbc:///?odbc_connect={}'.format('mssql', quote)
        elif self.config_type == 'accdb':
            return 'DRIVER={};DBQ={};Exclusive=1'.format('{Microsoft Access Driver (*.mdb, *.accdb)}',
                                                         self.accdb_fp)
        elif self.config_type == 'dsn':
            return 'DSN={};DATABASE=default;Trusted_Connection=Yes;'.format(self.dsn_name)
        elif self.config_type == 'conn_str':
            return self.conn_str
        else:
            return None

    def __eq__(self, other):
        if self.__slots__:
            for k in self.__slots__:
                if getattr(self, k) != getattr(other, k):
                    return False

            return True
        else:
            return False

    def __hash__(self):
        items = list()

        for item in self.__slots__:
            items.append(hash(getattr(self, item)))

        return items

    def __repr__(self):
        items = list()

        for item in self.__slots__:
            items.append(str(getattr(self, item)))

        return self.__class__.__name__ + repr(items)

    def __str__(self):
        items = list()

        for item in self.__slots__:
            items.append(str(getattr(self, item)))

        return ', '.join(items)
