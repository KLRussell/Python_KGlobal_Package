from __future__ import unicode_literals

from ..data.picklemixin import PickleMixIn
from threading import Lock
from datetime import datetime, timedelta
from time import sleep
from sqlalchemy import create_engine, exc, event, select
from sqlalchemy.engine import Engine
from pyodbc import Connection as Engine2, connect as create_engine2, Error, SQL_MAX_CONCURRENT_ACTIVITIES
from future.moves.queue import LifoQueue, Empty
from traceback import format_exc
from csv import QUOTE_ALL

import os
import logging

log = logging.getLogger(__name__)


class BaseSQLEngineClass(object):
    pass


class SQLEngineClass(BaseSQLEngineClass, PickleMixIn):
    """
        Defined SQL Engine class for connecting to SQL, executing commands, querying, uploading dataframes, and Transact
        commands (ie rollback, commit, and etc...)

        This is snapped out of a SQL engine queue and can be re-added to queue when not needed.
        """

    CONN_DEFAULT_TIMEOUT = 3
    QUERY_DEFAULT_TIMEOUT = 0
    DEFAULT_CONNECTION_SIZE = 10

    __slots__ = ("engine_type", "engine_id")

    def __init__(self, sql_config, conn_max_pool_size=DEFAULT_CONNECTION_SIZE, conn_timeout=CONN_DEFAULT_TIMEOUT,
                 query_timeout=QUERY_DEFAULT_TIMEOUT):
        """
        SQL Engine class initialization for SQL

        :param sql_config: SQLConfig class object for generating connection string
        :param conn_max_pool_size: [Optional] Pool size for multi-threaded connections
        :param conn_timeout: [Optional] Connection timeout for connecting to SQL Server, DSN, or Access Database
        :param query_timeout: [Optional] Query timeout for querying data DEFAULT is Infinity
        """

        from ..sql.config import SQLConfig

        if not isinstance(sql_config, SQLConfig):
            raise ValueError("'sql_config' %r is not an SQLConfig instance" % sql_config)

        self.__sql_config = sql_config
        self.engine_type = self.__sql_config.conn_type
        self.engine_id = sum(map(ord, str(os.urandom(100))))
        self.__conn_timeout = conn_timeout
        self.__query_timeout = query_timeout
        self.__cursors = LifoQueue(maxsize=conn_max_pool_size)
        self.__conn_max_pool_size = conn_max_pool_size
        self.__engine_lock = Lock()
        self.__cursor_results = list()
        self.__sql_handlers = list()
        self.__engine_sql_class = None
        self.__main_engine = None
        self.__main_spid = None

    @property
    def engine_spid(self):
        self.__main_engine, self.__main_spid = self.__validate_engine(self.__main_engine)

        if not self.__main_engine:
            self.__main_engine, self.__main_spid = self.connect()

        return [self.__main_engine, self.__main_spid]

    @property
    def cursors(self):
        """
        :return: List of cursor queue
        """

        return list(self.__cursors.queue)

    @property
    def sql_config(self):
        """
        :return: SQLConfig instance class
        """

        return self.__sql_config

    @property
    def get_engine_id(self):
        """

        :return: Engine Class Identifier
        """
        return self.engine_id

    @property
    def engine_sql_class(self):
        """
        :return: SQL Engine instance class
        """

        return self.__engine_sql_class

    @engine_sql_class.setter
    def engine_sql_class(self, engine_sql_class):
        from ..sql.queue import BaseSQLQueue

        if not isinstance(engine_sql_class, BaseSQLQueue):
            raise ValueError("'engine_sql_class' %r is not an instance of BaseSQLQueue" % engine_sql_class)

        self.__engine_sql_class = engine_sql_class

    @property
    def cursor_results(self):
        """
        Pulls list of completed cursors that returned an error or result set. List of class attributes are:
            * cursor_action
            * results
            * errors
            * is_pending

        :return: List of completed SQLCursor or EngineCursor class objects
        """
        return self.__cursor_results

    def connect(self, test_conn=False):
        """
        Connect to SQL Server, Access Database, or DSN by using the generated connection string from SQLConfig

        :param test_conn: [Optional] (True/False) Either Test connection or connect to SQL, Accdb, or DSN
        and keep connected
        :return: (True/False) if test connection was successful. No return result for regular connection
        """

        if self.engine_type == 'alchemy':
            engine = create_engine(
                self.__sql_config.gen_conn_str(), connect_args={
                    'timeout': self.__conn_timeout, 'connect_timeout': self.__conn_timeout,
                    'options': '-c statement_timeout=%s' % self.__query_timeout}
            )

            @event.listens_for(engine, "engine_connect")
            def ping_connection(connection, branch):
                if branch:
                    return

                try:
                    connection.scalar(select([1]))
                except exc.DBAPIError as err:
                    if err.connection_invalidated:
                        try:
                            connection.scalar(select([1]))
                        except exc.DBAPIError as err:
                            raise ValueError('Unable to connect %s' % err)
                    else:
                        raise ValueError('Unable to connect %s' % err)
                else:
                    if test_conn:
                        close_engine(engine)
                        return False

            engine.connect()
        else:
            engine = None

            try:
                engine = create_engine2(
                    self.__sql_config.gen_conn_str(), connect_args={
                        'timeout': self.__conn_timeout, 'connect_timeout': self.__conn_timeout,
                        'options': '-c statement_timeout=%s' % self.__query_timeout}
                )
                engine.commit()
            except Error as e:
                close_engine(engine)

                if test_conn:
                    return False
                else:
                    raise ValueError('Error! Code {0}, {1}'.format(type(e).__name__, str(e)))

        if test_conn:
            close_engine(engine)
            return True
        else:
            if self.engine_type == 'alchemy' and not isinstance(engine, Engine):
                raise ValueError("'engine' %r is not an Engine instance of SQLAlchemy Engine" % engine)
            if self.engine_type == 'pyodbc' and not isinstance(engine, Engine2):
                raise ValueError("'engine' %r is not an Engine instance of PYODBC Connection" % engine)

            engine, spid = self.__validate_engine(engine)
            log.debug('SQL Engine %s: Created connection (%s) on SPID %s', self.engine_id, str(self.__sql_config), spid)
            return [engine, spid]

    def restore_to_pool(self, close_cursors=False):
        """
        Puts SQLEngine class to SQL queue pool. Connection to engine is ensured before queing to pool

        :param close_cursors: [Optional] (True/False) Can choose to close all cursors before returning to pool
        """

        from ..sql.queue import SQLQueue

        if self.__engine_sql_class and isinstance(self.__engine_sql_class, SQLQueue):
            if close_cursors:
                self.__release_coms(kill_main_engine=True)

            self.__engine_sql_class.queue_sql_engine_to_pool(self)

    def stream_execute(self, buffer=1000):
        """
        Event Function
        Streams sql_execute by chunk for manual transformations and loading or transformations and storing into csv

        :param buffer: Number of lines per chunk to store in dataframe
        :var dataframe: Variable outputted to event function that is a buffered dataframe
        :var row_start: Row number for first row of data
        :var row_end: Row number for last row of data
        """

        def registerhandler(handler):
            self.__sql_handlers.append([handler, buffer])
            return handler

        return registerhandler

    def sql_execute(self, query_str, execute=False, queue_cursor=False, new_engine=False, csv_path=None,
                    csv_replace=False, delimiter=',', quotechar='"', quoting=QUOTE_ALL):
        """
        Execute or Query SQL query statement. This command can be multi-threaded in a cursor queue

        :param query_str: Query string that is executed to connection
        :param execute: [Optional] (True/False) Choose to execute or query results
        :param queue_cursor: [Optional] (True/False) Add to multi-thread queue
        :param new_engine: [Optional] (True/False) creates new engine for threading
        :param csv_path: File path where data is stored at for csv file
        :param csv_replace: (Optional) [True/False] Replace csv file if exists
        :param delimiter: Data seperator to delimit columns
        :param quotechar: Quote Character to wrap values with
        :param quoting: csv quote mode

        :return: Returns Cursor class if queue_cursor is set to False
        """

        if new_engine or queue_cursor:
            engine, spid = self.connect()
            keep_engine_alive = False
        else:
            engine, spid = self.engine_spid
            keep_engine_alive = True

        if new_engine:
            self.__execute_sql(engine, spid, keep_engine_alive, query_str, execute, queue_cursor, csv_path,
                               csv_replace, delimiter, quotechar, quoting)
        else:
            with self.__engine_lock:
                self.__execute_sql(engine, spid, keep_engine_alive, query_str, execute, queue_cursor, csv_path,
                                   csv_replace, delimiter, quotechar, quoting)

    def __execute_sql(self, engine, spid, keep_engine_alive, query_str, execute=False, queue_cursor=False,
                      csv_path=None, csv_replace=False, delimiter=',', quotechar='"', quoting=QUOTE_ALL):
        from ..sql.cursor import SQLCursor

        if queue_cursor:
            params = dict(query_str=query_str, execute=execute, handlers=self.__sql_handlers, csv_path=csv_path,
                          csv_replace=csv_replace, delimiter=delimiter, quotechar=quotechar, quoting=quoting)
            cursor = SQLCursor(engine_type=self.engine_type, engine=engine, spid=spid, engine_class=self,
                               action="execute", action_params=params, keep_engine_alive=keep_engine_alive)

            try:
                self.__cursors.put(cursor, block=False)
                cursor.start()
            except:
                cursor.close()
        elif self.__sql_handlers:
            for handler, buffer in self.__sql_handlers:
                cursor = SQLCursor(engine_type=self.engine_type, engine=engine, spid=spid,
                                   keep_engine_alive=keep_engine_alive)

                try:
                    cursor.start()
                    cursor.execute(query_str=query_str, execute=execute, handler=handler, buffer=buffer,
                                   csv_path=csv_path, csv_replace=csv_replace, delimiter=delimiter,
                                   quotechar=quotechar, quoting=quoting)
                    cursor.join()
                except Exception as e:
                    cursor.close()
                    log.debug(format_exc())
                else:
                    return cursor
        else:
            cursor = SQLCursor(engine_type=self.engine_type, engine=engine, spid=spid,
                               keep_engine_alive=keep_engine_alive)

            try:
                cursor.start()
                cursor.execute(query_str=query_str, execute=execute, csv_path=csv_path, csv_replace=csv_replace,
                               delimiter=delimiter, quotechar=quotechar, quoting=quoting)
                cursor.join()
            except:
                cursor.close()
                log.debug(format_exc())
            else:
                return cursor

    def sql_upload(self, dataframe, table_name, table_schema=None, if_exists='append', index=True, index_label='ID',
                   queue_cursor=False, new_engine=False):
        """
        SQL Alchemy's command to upload a Dataframe to the SQL connection

        :param dataframe: Panda's Dataframe
        :param table_name: Table name in destination
        :param table_schema: Table schema in destination
        :param if_exists: [Optional] (append/replace) If table exists, should I append or replace table?
        :param index: [Optional] (True/False) Should generated indexes from dataframe be uploaded?
        :param index_label: [Optional] What is the index column name (Use when Index is True)
        :param queue_cursor: [Optional] (True/False) Add to multi-thread queue
        :param new_engine: [Optional] (True/False) creates new engine for threading
        :return: Returns Cursor class if queue_cursor is set to False
        """

        if self.engine_type == 'alchemy':
            if new_engine or queue_cursor:
                engine, spid = self.connect()
                keep_engine_alive = False
            else:
                engine, spid = self.engine_spid
                keep_engine_alive = True

            if new_engine:
                self.__sql_upload(engine, spid, keep_engine_alive, dataframe, table_name, table_schema, if_exists,
                                  index, index_label, queue_cursor)
            else:
                with self.__engine_lock:
                    self.__sql_upload(engine, spid, keep_engine_alive, dataframe, table_name, table_schema, if_exists,
                                      index, index_label, queue_cursor)

    def __sql_upload(self, engine, spid, keep_engine_alive, dataframe, table_name, table_schema=None,
                     if_exists='append', index=True, index_label='ID', queue_cursor=False):
        from ..sql.cursor import EngineCursor

        if queue_cursor:
            params = dict(dataframe=dataframe, table_name=table_name, table_schema=table_schema,
                          if_exists=if_exists, index=index, index_label=index_label)
            cursor = EngineCursor(alch_engine=engine, spid=spid, engine_class=self, action='upload_df',
                                  action_params=params, keep_engine_alive=keep_engine_alive)

            try:
                self.__cursors.put(cursor, block=False)
                cursor.start()
            except:
                cursor.close()
        else:
            cursor = EngineCursor(alch_engine=engine, spid=spid, keep_engine_alive=keep_engine_alive)

            try:
                cursor.start()
                cursor.upload_df(dataframe, table_name, table_schema, if_exists, index, index_label)
                cursor.join()
            except:
                cursor.close()
                log.debug(format_exc())
            else:
                return cursor

    def sql_tables(self, queue_cursor=False, new_engine=False):
        """
        Retreive full table list from the SQL connection

        :param queue_cursor: (True/False) Add to multi-thread queue
        :param new_engine: [Optional] (True/False) creates new engine for threading
        :return: Returns Cursor class if queue_cursor is set to False
        """

        if new_engine or queue_cursor:
            engine, spid = self.connect()
            keep_engine_alive = False
        else:
            engine, spid = self.engine_spid
            keep_engine_alive = True

        if new_engine:
            self.__sql_tables(engine, spid, keep_engine_alive, queue_cursor)
        else:
            with self.__engine_lock:
                self.__sql_tables(engine, spid, keep_engine_alive, queue_cursor)

    def __sql_tables(self, engine, spid, keep_engine_alive, queue_cursor=False):
        from ..sql.cursor import SQLCursor

        cursor = SQLCursor(engine_type=self.engine_type, engine=engine, spid=spid, keep_engine_alive=keep_engine_alive)

        try:
            if queue_cursor:
                cursor.start()
                cursor.engine_class = self
                self.__cursors.put(cursor, block=False)
                cursor.tables()
            else:
                cursor.start()
                cursor.tables()
                cursor.join()
        except:
            cursor.close()
            log.debug(format_exc())
        else:
            if not queue_cursor and cursor:
                return cursor

    def wait_for_cursors(self, timeout=0):
        """
        Waits for all cursors to be completed and returns result sets

        :param timeout: [Optional] Seconds to wait before timing out (0 is infinity)
        :return: Cursor Result listset
        """

        if self.__cursors.qsize() > 0:
            if timeout < 0:
                raise ValueError("'timeout' must be a non-negative number")

            with self.__engine_lock:
                curr_time = datetime.now()
                end_time = datetime.now() + timedelta(seconds=timeout)

                try:
                    while (curr_time < end_time or timeout == 0) and len(self.cursors) > 0:
                        curr_time = datetime.now()
                        sleep(1)

                    if len(self.cursors) > 0:
                        raise ValueError("Not all cursors are complete. Operation timed out")
                    else:
                        return self.__cursor_results
                except:
                    self.__release_coms()
        else:
            return self.__cursor_results

    def close_connections(self, destroy_self=False, enable_log=True):
        """
        Closes all cursors and engines

        :param destroy_self: (True/False) Request self destruction of class
        :param enable_log: (True/False) Enables logging
        """

        if enable_log:
            log.debug('SQL Connection (%s): Releasing SQL engine %s', str(self.__sql_config), self.engine_id)

        self.__release_coms(enable_log=enable_log, kill_main_engine=True)

        if destroy_self and self.__engine_sql_class:
            self.__engine_sql_class.remove_engine_from_pool(self)

    def add_cursor_result(self, cursor_result):
        """
         Adds SQLCursor or EngineCursor instance class results to list

        :param cursor_result: SQLCursor or EngineCursor instance class
        """

        self.__cursor_results.append(cursor_result)

    def rem_cursor(self, cursor):
        """
        Removes a SQLCursor or EngineCursor instance class from results list
        :param cursor: SQLCursor or EngineCursor instance class
        """

        if len(self.__cursors.queue) > 0:
            self.__cursors.queue.remove(cursor)

    def __validate_engine(self, engine):
        spid = None

        if engine is not None:
            if self.engine_type == 'alchemy':
                raw_engine = engine.raw_connection()
            else:
                raw_engine = engine

            cursor = raw_engine.cursor()

            try:
                dataset = cursor.execute("SELECT @@SPID")
                spid = [tuple(t) for t in dataset.fetchall()][0]
            except:
                engine = None
                pass
            finally:
                try:
                    cursor.close()
                except:
                    pass

        return [engine, spid]

    def __release_coms(self, enable_log=True, kill_main_engine=False):
        if self.__cursors.qsize() > 0:
            with self.__engine_lock:
                if kill_main_engine:
                    close_engine(self.__main_engine)

                self.__main_engine = None
                self.__main_spid = None

                while True:
                    try:
                        self.__cursors.get(block=False).close(write_log=enable_log)
                    except Empty:
                        break

    def __del__(self):
        self.__release_coms(kill_main_engine=True)

    def __getstate__(self):
        # The pool and lock cannot be pickled
        self.__release_coms(kill_main_engine=True)
        state = self.__dict__.copy()

        if state and '__cursors' in state.keys():
            del state['__cursors']

        if state and '__engine_lock' in state.keys():
            del state['__engine_lock']

        return state

    def __setstate__(self, state):
        # Restore the pool and lock
        self.__dict__.update(state)
        self.__cursors = LifoQueue(maxsize=self.__conn_max_pool_size)
        self.__engine_lock = Lock()
        self.connect()

    def __eq__(self, other):
        for k in self.__slots__:
            if getattr(self, k) != getattr(other, k):
                return False

        return True

    def __hash__(self):
        return hash(self.engine_id)

    def __repr__(self):
        return self.__class__.__name__ + repr(str(self.engine_id))

    def __str__(self):
        return str(self.engine_id)


def close_engine(engine):
    if engine and hasattr(engine, 'cancel'):
        try:
            engine.cancel()
        except:
            pass

    if engine and hasattr(engine, 'connection') and hasattr(engine.connection, 'cancel'):
        try:
            engine.connection.cancel()
        except:
            pass

    if engine and hasattr(engine, 'connection') and hasattr(engine.connection, 'close'):
        try:
            engine.connection.close()
        except:
            pass

    if engine and hasattr(engine, 'close'):
        try:
            engine.close()
        except:
            pass

    if engine and isinstance(engine, Engine) and hasattr(engine, 'dispose'):
        try:
            engine.dispose()
        except:
            pass