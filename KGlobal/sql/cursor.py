from __future__ import unicode_literals

from threading import Thread, Lock
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from pyodbc import Error as PYODBCError
from pandas import DataFrame
from csv import writer as csv_writer, QUOTE_ALL
from types import FunctionType, BuiltinFunctionType, MethodType, BuiltinMethodType

import logging
import os

log = logging.getLogger(__name__)


class SQLCursor(Thread):
    """
    A SQLCursor class to handle SQLEngine's cursor's when executing queries or retrieving server tables
    -   Class is threaded thus multiple cursors can be executing in a queue at the same time
    """

    __cursor = None
    __engine_class = None
    __cursor_action = None

    def __init__(self, engine_type, engine, spid, keep_engine_alive=True, engine_class=None, action=None,
                 action_params=None):
        """
        Creates a SQLCursor class instance that handles engine cursor operations

        :param engine: engine that is generated from SQLEngine's instance class
        :param engine_class: SQLEngine class instance
        :param action: [execute, tables]
        :param action_params: Action parameters according to execute or tables command below
        """

        if engine_type not in ['alchemy', 'pyodbc']:
            raise ValueError("'engine_type' %r is not alchemy or pyodbc" % engine_type)
        if action and action not in ('execute', 'tables'):
            raise ValueError("'action' is not execute or tables")

        self.__engine_type = engine_type
        self.__engine = engine
        self.__spid = spid
        self.engine_class = engine_class
        self.__raw_engine = None
        self.__keep_engine_alive = keep_engine_alive

        if engine_type == 'alchemy':
            self.__raw_engine = self.__engine.raw_connection()
            engine = self.__raw_engine
        else:
            engine = self.__engine

        self.__cursor = engine.cursor()
        if action:
            self.__cursor_action = [action, action_params]
        self.__execute_errors = None
        self.__execute_results = None
        self.__is_pending = Lock()
        self.__is_closing = Lock()
        self.cursor_id = sum(map(ord, str(os.urandom(100))))
        super(SQLCursor, self).__init__()

    @property
    def cursor_action(self):
        """
        :return: Returns cursor action that was performed
        """

        return self.__cursor_action

    @property
    def results(self):
        """
        :return: Return one or more datasets retreived from execution of sql command
        """

        return self.__execute_results

    @property
    def errors(self):
        """
        :return: Returns one or more errors that occurred from execution of sql command
        """

        return self.__execute_errors

    @property
    def is_pending(self):
        """
        :return: Returns True/False when cursor is actively processing an action
        """

        return self.__is_pending.locked()

    @property
    def engine_class(self):
        """
        :return: Returns SQLEngine class instance that may be tied to this class
        """

        return self.__engine_class

    @engine_class.setter
    def engine_class(self, engine_class):
        from ..sql.engine import SQLEngineClass

        if not isinstance(engine_class, (SQLEngineClass, type(None))):
            raise ValueError("'engine_class' %r is not an instance of SQLEngineClass" % engine_class)

        self.__engine_class = engine_class

    def run(self):
        """
        Run operator that is executed upon creation of this SQLCursor class instance
        """

        if self.__cursor_action:
            function, params = self.__cursor_action

            if function == 'execute':
                if 'query_str' not in params.keys():
                    raise ValueError("'query_str' was not provided as action_param when class ran")
                if 'execute' not in params.keys():
                    params['execute'] = None

                if 'handlers' in params.keys():
                    for handler, buffer, csv_path, delimiter, quotechar in params['handlers']:
                        self.execute(query_str=params['query_str'], execute=params['execute'], handler=handler,
                                     buffer=buffer, csv_path=csv_path, delimiter=delimiter, quotechar=quotechar)
                else:
                    self.execute(query_str=params['query_str'], execute=params['execute'])
            elif function == 'tables':
                self.tables()
            elif function is not None:
                raise ValueError("'function' is an invalid function command")

    def close(self, write_log=True):
        """
        Closes cursor comm, pop SQLCursor instance class out of SQLEngine's cursor queue and add to results list in
        SQLEngine's class instance

        :param write_log: (Optional) [True/False]
        """

        with self.__is_closing:
            if self.__cursor and hasattr(self.__cursor, 'cancel'):
                try:
                    if write_log:
                        if self.__engine_class:
                            log.debug('SQL Connection (%s): Canceling & Closing SQL cursor %s transaction',
                                      self.__engine_class.get_engine_id, self.cursor_id)
                        else:
                            log.debug('Canceling & Closing SQL cursor %s transaction', self.cursor_id)

                    self.__cursor.cancel()
                except:
                    pass
                finally:
                    self.__close()

    def rollback(self, write_log=True):
        """
        Rollsback cursor comm and executes close() operations within SQLCursor class instance

        :param write_log: (Optional) [True/False]
        """

        with self.__is_closing:
            if self.__cursor and hasattr(self.__cursor, 'rollback'):
                try:
                    if write_log:
                        if self.__engine_class:
                            log.debug('SQL Connection (%s): Rollback & Close SQL cursor %s transaction',
                                      self.__engine_class.get_engine_id, self.cursor_id)
                        else:
                            log.debug('Rollback & Close SQL cursor %s transaction', self.cursor_id)

                    self.__cursor.rollback()
                except:
                    pass
                finally:
                    self.__close()

    def commit(self, write_log=True):
        """
        Commit cursor comm and executes close() operations within SQLCursor class instance

        :param write_log: (Optional) [True/False]
        """

        try:
            with self.__is_closing:
                if self.__cursor and hasattr(self.__cursor, 'commit'):
                    if write_log:
                        if self.__engine_class:
                            log.debug('SQL Connection (%s): Commit & Close SQL cursor %s transaction',
                                      self.__engine_class.get_engine_id, self.cursor_id)
                        else:
                            log.debug('Commit & Close SQL cursor %s transaction', self.cursor_id)

                    self.__cursor.commit()
                    self.__close()
        except:
            self.rollback()
            pass

    def __close(self):
        from .engine import close_engine

        if self.__cursor and hasattr(self.__cursor, 'close'):
            try:
                self.__cursor.close()
            except:
                pass

        if not self.__keep_engine_alive:
            close_engine(self.__engine)

        if self.__engine_class:
            if self.__execute_results or self.__execute_errors:
                self.__engine_class.add_cursor_result(self)

            self.__engine_class.rem_cursor(self)

        self.__engine = None
        self.__raw_engine = None
        self.__cursor = None

    def tables(self):
        """
        Requests sql connection to pull [table_type, table_cat, table_schema, table_name] and store it in a dataframe.
        Dataframe is appended to the results attribute of this class
        """

        if self.__cursor:
            try:
                if not self.__cursor_action:
                    self.__cursor_action = ['tables', None]

                with self.__is_pending:
                    log.debug("Retreiving tables on SPID %s" % self.__spid)
                    self.__execute_results = list()
                    tables = [[t.table_type, t.table_cat, t.table_schem, t.table_name] for t in self.__cursor.tables()]

                    if tables:
                        self.__execute_results.append(DataFrame(tables, columns=['Table_Type', 'Table_Cat',
                                                                                 'Table_Schema', 'Table_Name']))
                    else:
                        self.__execute_results.append(DataFrame())

                    self.__close()
            except SQLAlchemyError as e:
                self.__execute_errors = [e.code, e.__dict__['orig']]
                self.rollback()
            except PYODBCError as e:
                self.__execute_errors = [e.args[0], e.args[1]]
                self.rollback()
            except (AttributeError, Exception) as e:
                self.__execute_errors = [type(e).__name__, str(e)]
                self.rollback()
        else:
            raise Exception("Cursor is closed. Cannot pull tables")

    def execute(self, query_str, execute=False, handler=None, buffer=1000, csv_path=None, csv_replace=False,
                delimiter=',', quotechar='"', quoting=QUOTE_ALL):
        """
        Requests sql connection to execute or query a sql query string. Execution of TSQL queries will follow
        commit and rollback commands when necessary. Results are appended to the results and/or errors attributes

        :param query_str: SQL query string
        :param execute: (Optional) [True/False] Default is False
        :param handler: (Optional) Function or Class Function handler
        :param buffer: (Optional) [handler only] Number of lines per chunk to store in dataframe
        :param csv_path: (Optional) [handler only] File path where data is stored at for csv file
        :param csv_replace: (Optional) [True/False] Replace csv file if exists
        :param delimiter: (Optional) [handler only] Data seperator to delimit columns
        :param quotechar: (Optional) [handler only] Quote Character to wrap values with
        """

        if handler:
            if not isinstance(handler, (FunctionType, BuiltinFunctionType, MethodType, BuiltinMethodType)):
                raise ValueError("'handler' %r is not a function" % handler)
            if not isinstance(buffer, int):
                raise eError("'buffer' %r is not a int" % buffer)
            if csv_path and not isinstance(csv_path, str):
                raise ValueError("'csv_path' %r is not a str" % csv_path)
            if not isinstance(delimiter, str):
                raise ValueError("'delimiter' %r is not a str" % delimiter)
            if not isinstance(quotechar, str):
                raise ValueError("'quotechar' %r is not a str" % quotechar)

            buffer = int(buffer)

            if buffer < 1:
                raise ValueError("'buffer' %r value is zero or negative" % buffer)
            if csv_path and not os.path.exists(os.path.dirname(csv_path)):
                raise ValueError("'csv_path' %r is not a valid directory path" % os.path.dirname(csv_path))
            if csv_path and not csv_path.endswith('.csv'):
                raise ValueError("'csv_path' %r is does not have a .csv extension" % os.path.basename(csv_path))

            if csv_path and csv_replace and os.path.exists(csv_path):
                try:
                    os.remove(csv_path)
                except:
                    pass

            if csv_path and os.path.exists(csv_path):
                raise ValueError("'csv_path' %r file exists already" % csv_path)

        if self.__cursor:
            if not isinstance(query_str, str):
                raise ValueError("'query_str' %r is not a String" % query_str)

            try:
                if not self.__cursor_action:
                    self.__cursor_action = ['execute', dict(query_str=query_str, execute=execute)]

                with self.__is_pending:
                    log.debug("Executing on SPID {0} query [{1}]".format(self.__spid, query_str))
                    self.__execute_results = list()
                    result = self.__cursor.execute(query_str)

                    if handler:
                        self.__stream_dataset(result, handler, buffer, csv_path, delimiter, quotechar, quoting)
                    else:
                        self.__store_dataset(result)

                    while result.nextset():
                        if handler:
                            self.__stream_dataset(result, handler, buffer, csv_path, delimiter, quotechar, quoting)
                        else:
                            self.__store_dataset(result)

                    if execute:
                        self.commit()
                    else:
                        self.__close()
            except SQLAlchemyError as e:
                self.__execute_errors = [e.code, e.__dict__['orig']]
                self.rollback()
            except PYODBCError as e:
                self.__execute_errors = [e.args[0], e.args[1]]
                self.rollback()
            except (AttributeError, Exception) as e:
                from traceback import format_exc
                print(format_exc())
                self.__execute_errors = [type(e).__name__, str(e)]
                self.rollback()
        else:
            raise Exception("Cursor is closed. Cannot execute query")

    def __store_dataset(self, dataset):
        try:
            data = [tuple(t) for t in dataset.fetchall()]
            cols = [column[0] for column in dataset.description]
            self.__execute_results.append(DataFrame(data, columns=cols))
        except:
            pass

    def __stream_dataset(self, dataset, handler, buffer, csv_path, delimiter, quotechar, quoting):
        cols = [column[0] for column in dataset.description]
        buffer_list = list()
        row_num = 0

        for row in dataset:
            buffer_list.append(tuple(row))

            if buffer <= len(buffer_list):
                self.__handle_buffer(row_num, cols, buffer_list, handler, csv_path, delimiter, quotechar, quoting)
                buffer_list.clear()

            row_num += 1

        self.__handle_buffer(row_num - 1, cols, buffer_list, handler, csv_path, delimiter, quotechar, quoting)

    @staticmethod
    def __handle_buffer(row_num, cols, buffer_list, handler, csv_path, delimiter, quotechar, quoting):
        if buffer_list:
            df = DataFrame(buffer_list, columns=cols)

            if csv_path:
                hreturn = handler(df, row_num - len(buffer_list) + 1, row_num)

                if hreturn and isinstance(hreturn, DataFrame):
                    df = hreturn

                if row_num - len(buffer_list) + 1 == 0:
                    mode = 'w'
                    header = True
                else:
                    mode = 'a'
                    header = False

                df.to_csv(path_or_buf=csv_path, sep=delimiter, quotechar=quotechar, mode=mode, index=False,
                          header=header, quoting=quoting)
            else:
                handler(df, row_num - len(buffer_list) + 1, row_num)


class EngineCursor(Thread):
    """
    Engine Cursor class for SQLAlchemy connections. Primary purpose of this class is to utilize dataframe to_upload()
    """

    __engine = None
    __engine_class = None

    def __init__(self, alch_engine, spid, keep_engine_alive=True, engine_class=None, action=None, action_params=None):
        """
        Creates a EngineCursor class instance and run an action with parameters upon class creation

        :param alch_engine: SQLAlchemy engine
        :param engine_class: (Optional) SQLEngine instance class
        :param action: (Optional) [upload]
        :param action_params: (Optional) upload_df() command parameters
        """

        if not isinstance(alch_engine, Engine):
            raise ValueError("'alch_engine' %r is not an Alchemy Engine instance" % alch_engine)

        if action and action != 'upload_df':
            raise ValueError("'action' is not upload_df")

        self.engine_class = engine_class
        self.__engine = alch_engine
        self.__spid = spid
        self.__keep_engine_alive = keep_engine_alive
        self.__cursor_action = [action, action_params]
        self.__is_pending = Lock()
        self.__is_closing = Lock()
        self.__errors = None
        self.cursor_id = sum(map(ord, str(os.urandom(100))))
        super(EngineCursor, self).__init__()

    @property
    def cursor_action(self):
        """
        :return: Returns cursor action that was performed
        """

        return self.__cursor_action

    @property
    def results(self):
        """
        :return: Return one or more datasets retreived from execution of sql command
        """

        return None

    @property
    def errors(self):
        """
        :return: Returns one or more errors that occurred from execution of sql command
        """

        return self.__errors

    @property
    def is_pending(self):
        """
        :return: Returns True/False when cursor is actively processing an action
        """

        return self.__is_pending.locked()

    @property
    def engine_class(self):
        return self.__engine_class

    @engine_class.setter
    def engine_class(self, engine_class):
        from ..sql.engine import SQLEngineClass

        if not isinstance(engine_class, (SQLEngineClass, type(None))):
            raise ValueError("'engine_class' %r is not an instance of SQLEngineClass" % engine_class)

        self.__engine_class = engine_class

    def run(self):
        """
        Run operator that is executed upon creation of this SQLCursor class instance
        """

        if self.__cursor_action:
            function, params = self.__cursor_action

            if function == 'upload_df':
                if 'dataframe' not in params.keys():
                    raise ValueError("'dataframe' was not provided as action_param when class ran")
                if 'table_name' not in params.keys():
                    raise ValueError("'table_name' was not provided as action_param when class ran")
                if 'table_schema' not in params.keys():
                    params['table_schema'] = None
                if 'if_exists' not in params.keys():
                    params['if_exists'] = None
                if 'index' not in params.keys():
                    params['index'] = None
                if 'index_label' not in params.keys():
                    params['index_label'] = None

                self.upload_df(dataframe=params['dataframe'], table_name=params['table_name'],
                               table_schema=params['table_schema'], if_exists=params['if_exists'],
                               index=params['index'], index_label=params['index_label'])
            elif function is not None:
                raise ValueError("'function' %s is an invalid function command" % function)

    def close(self):
        """
        Closes cursor comm, pop SQLCursor instance class out of SQLEngine's cursor queue and add to results list in
        SQLEngine's class instance
        """

        with self.__is_closing:
            if self.__engine:
                from .engine import close_engine

                try:
                    if hasattr(self.__engine, 'cancel'):
                        self.__engine.cancel()

                    if hasattr(self.__engine, 'rollback'):
                        self.__engine.rollback()
                except SQLAlchemyError as e:
                    log.error(e.code, e.__dict__['orig'])
                    pass

                if not self.__keep_engine_alive:
                    close_engine(self.__engine)

            self.__engine = None

    def upload_df(self, dataframe, table_name, table_schema=None, if_exists='append', index=True, index_label='ID'):
        """
        Uploads a pandas DataFrame to a sql table

        :param dataframe: pandas Dataframe
        :param table_name: SQL table name
        :param table_schema: (Optional) SQL table schema
        :param if_exists: (Optional) [append, replace]
        :param index: (Optional) [True, False] Default is True
        :param index_label: (Optional) Default is ID
        """

        if self.__engine:
            if not isinstance(dataframe, DataFrame):
                raise ValueError("'dataframe' %r is not an pandas Dataframe instance" % dataframe)
            if not isinstance(table_name, str):
                raise ValueError("'table_name' %r is not a String" % table_name)
            if not isinstance(table_schema, (str, type(None))):
                raise ValueError("'table_schema' %r is not a String" % table_schema)

            if not self.__cursor_action:
                params = dict(dataframe=dataframe, table_name=table_name, table_schema=table_schema,
                              if_exists=if_exists, index=index, index_label=index_label)
                self.__cursor_action = ['upload_df', params]

            with self.__is_pending:
                log.debug("SQL Upload on SPID {0} to [{1}]".format(self.__spid, '{0}.{1}'.join(table_schema,
                                                                                               table_name)))

                try:
                    dataframe.to_sql(
                        table_name,
                        self.__engine,
                        schema=table_schema,
                        if_exists=if_exists,
                        index=index,
                        index_label=index_label,
                        chunksize=1000
                    )
                except SQLAlchemyError as e:
                    self.__errors = [e.code, e.__dict__['orig']]
                    self.close()
                except (AttributeError, Exception) as e:
                    self.__errors = [type(e).__name__, str(e)]
                    self.close()
                else:
                    self.__close()
        else:
            raise ValueError('Engine is closed. Unable to upload dataframe')

    def __close(self):
        if self.__engine_class:
            if self.__errors:
                self.__engine_class.add_cursor_result(self)

            self.__engine_class.rem_cursor(self)
        else:
            self.__engine = None
