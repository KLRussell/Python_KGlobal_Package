from __future__ import unicode_literals

from future.moves.queue import LifoQueue, Empty
from threading import Lock
from ..data.error import TransportError

import logging
import os

log = logging.getLogger(__name__)


def close_sql_connections():
    CatchSQLQueue.clear_cache()


class BaseSQLQueue(object):
    CONN_DEFAULT_TIMEOUT = 3
    QUERY_DEFAULT_TIMEOUT = 0
    DEFAULT_CONNECTION_SIZE = 10

    def __init__(self, queue_id, pool_size):
        """
        Class to add different SQL engines to a pool

        :param queue_id: [Optional] Queue_ID
        :param pool_size: [Optional] Pool_Size for SQL engines
        """

        self.__queue_id = queue_id
        self.__pool_size = pool_size
        self.__sql_engine_pool = LifoQueue(maxsize=pool_size)
        self.__sql_engine_pool_lock = Lock()
        self.__disabled_pool = list()

    @property
    def pool_list(self):
        """
        :return: Returns list of engines in pool Queue
        """

        if self.__disabled_pool:
            raise Exception("Pool is currently disabled. Unable to view items")
        else:
            return list(self.__sql_engine_pool.queue)

    @property
    def max_pool_size(self):
        """
        :return: Returns Engine pool max size
        """

        if self.__disabled_pool:
            raise Exception("Pool is currently disabled. Unable to get size of pool")
        else:
            return self.__pool_size

    @max_pool_size.setter
    def max_pool_size(self, max_pool_size):
        """
        Sets Max pool size for engine queue

        :param max_pool_size: New max pool size
        """

        if max_pool_size < 1:
            raise ValueError("'max_pool_size' %s is a negative number" % max_pool_size)

        self.__pool_size = max_pool_size

    def create_sql_engine_to_pool(self, sql_config, conn_max_pool_size=DEFAULT_CONNECTION_SIZE,
                                  conn_timeout=CONN_DEFAULT_TIMEOUT, query_timeout=QUERY_DEFAULT_TIMEOUT):
        """
        Creates a new SQL engine and queues it into the engine queue pool

        :param sql_config: SQLConfig instance class
        :param conn_max_pool_size: Max SQL connection pool size
        :param conn_timeout: SQL Connection timeout in seconds
        :param query_timeout: SQL Query timeout in seconds
        """

        from .engine import SQLEngineClass

        if not self.__disabled_pool:
            with self.__sql_engine_pool_lock:
                sql_engine = SQLEngineClass(sql_config=sql_config, conn_max_pool_size=conn_max_pool_size,
                                            conn_timeout=conn_timeout, query_timeout=query_timeout)
                sql_engine.connect()
                sql_engine.engine_sql_class = self

            self.queue_sql_engine_to_pool(sql_engine)
        else:
            log.error('Queue Pool %s: Is in disabled state. Please enable', self.__queue_id)

    def queue_sql_engine_to_pool(self, sql_engine):
        """
        Puts SQLEngine class instance back into the sql queue pool if queue pool has room available

        :param sql_engine: SQLEngine class instance
        """

        from .engine import SQLEngineClass

        if not self.__disabled_pool:
            if not isinstance(sql_engine, SQLEngineClass):
                raise ValueError("'engine' %r is not an instance of SQLEngineClass")

            if sql_engine not in self.__sql_engine_pool.queue:
                with self.__sql_engine_pool_lock:
                    log.debug('Queue Pool %s: Added SQL engine %s to pool', self.__queue_id, sql_engine.engine_id)
                    self.__sql_engine_pool.put(sql_engine, block=False)
        else:
            log.error('Queue Pool %s: Is in disabled state. Please enable', self.__queue_id)

    def pop_sql_engine_from_pool(self):
        """
        Removes sql engine from top of SQL queue pool and returns engine to user

        :return: Returns SQLEngine class instance object
        """

        if not self.__disabled_pool:
            with self.__sql_engine_pool_lock:
                _timeout = 60

                while True:
                    try:
                        log.debug('Queue Pool %s: Waiting for SQL engine', self.__queue_id)
                        sql_engine = self.__sql_engine_pool.get(timeout=_timeout)
                        log.debug('Queue Pool %s: Popped SQL engine %s from pool', self.__queue_id,
                                  sql_engine.engine_id)
                        return sql_engine
                    except Empty:
                        log.debug('Queue Pool %s: No SQL engines available for %s seconds', self.__queue_id, _timeout)
        else:
            log.error('Queue Pool %s: Is in disabled state. Please enable', self.__queue_id)

    def remove_engine_from_pool(self, sql_engine):
        """
        Removes SQLEngine class instance for sql queue pool

        :param sql_engine: SQLEngine class instance
        """

        from .engine import SQLEngineClass

        if not self.__disabled_pool:
            if not isinstance(sql_engine, SQLEngineClass):
                raise ValueError("'engine' %r is not an instance of SQLEngineClass")
            if sql_engine not in self.__sql_engine_pool.queue:
                raise ValueError("'engine' %r is not in the SQL Engine Pool" % sql_engine)

            with self.__sql_engine_pool_lock:
                log.debug('Queue Pool %s: Removed SQL engine %s from pool', self.__queue_id, sql_engine.engine_id)
                self.__sql_engine_pool.queue.remove(sql_engine)
        else:
            log.error('Queue Pool %s: Is in disabled state. Please enable', self.__queue_id)

    def close_pool(self):
        """
        Closes all connections, cursors from all SQLEngines stored in sql queue pool and empty pool
        """

        with self.__sql_engine_pool_lock:
            log.debug('Queue Pool %s: Closing SQL Engine pool', self.__queue_id)

            while True:
                try:
                    self.__sql_engine_pool.get(block=False).close_connections(False)
                except Empty:
                    break

    def disable_pool(self):
        """
        Closes all connections, cursors from all SQLEngines stored in sql queue pool and disabled sql queue pool
        """

        if not self.__disabled_pool:
            with self.__sql_engine_pool_lock:
                log.debug('Queue Pool %s: Disabling SQL Engine pool', self.__queue_id)

                while True:
                    try:
                        sql_engine = self.__sql_engine_pool.get(block=False)
                        sql_engine.close_connections()
                        self.__disabled_pool.append(sql_engine)
                    except Empty:
                        break
        else:
            log.warning('Queue Pool %s: Is already disabled', self.__queue_id)

    def enable_pool(self):
        """
        Enables sql queue pool and reconnect all SQLEngine instance classes in pool
        """

        if self.__disabled_pool:
            with self.__sql_engine_pool_lock:
                log.debug('Queue Pool %s: Enabling SQL Engine pool', self.__queue_id)

                for sql_engine in self.__disabled_pool:
                    sql_engine.connect()
                    self.__sql_engine_pool.put(sql_engine, block=False)

                self.__disabled_pool = list()
        else:
            log.warning('Queue Pool %s: Is already enabled', self.__queue_id)

    def __del__(self):
        self.close_pool()

    def __getstate__(self):
        # The pool and lock cannot be pickled
        self.disable_pool()
        state = self.__dict__.copy()
        del state['__sql_engine_pool']
        del state['__sql_engine_pool_lock']
        return state

    def __setstate__(self, state):
        # Restore the pool and lock
        self.__dict__.update(state)
        self.__sql_engine_pool = LifoQueue(maxsize=self.__pool_size)
        self.__sql_engine_pool_lock = Lock()
        self.enable_pool()


class CatchSQLQueue(type):
    SQL_POOLSIZE = 10
    _sql_queue_cache = {}
    _sql_queue_cache_lock = Lock()

    def __call__(cls, queue_id=sum(map(ord, str(os.urandom(100)))), pool_size=SQL_POOLSIZE):
        _sql_queue_cache_key = queue_id
        sql = cls._sql_queue_cache.get(_sql_queue_cache_key)

        if isinstance(sql, Exception):
            raise sql
        if sql:
            return sql

        log.debug('Waiting for _sql_queue_cache_lock')

        with cls._sql_queue_cache_lock:
            sql = cls._sql_queue_cache.get(_sql_queue_cache_key)

            if isinstance(sql, Exception):
                raise sql
            if sql:
                return sql

            log.debug("SQLQueue __call__ cache miss. Adding key '%s'", str(_sql_queue_cache_key))

            try:
                sql = super(CatchSQLQueue, cls).__call__(queue_id, pool_size)
            except TransportError as e:
                log.warning('Failed to create cached SQLQueue with key %s: %s', _sql_queue_cache_key, e)
                cls._sql_queue_cache[_sql_queue_cache_key] = e
                raise e

            cls._sql_queue_cache[_sql_queue_cache_key] = sql
            return sql

    @classmethod
    def clear_cache(mcs):
        for key, sql_queue in mcs._sql_queue_cache.items():
            if isinstance(sql_queue, Exception):
                continue

            conn_config = key[0]
            log.debug("Conn Config '%s': Closing SQL connections", conn_config)
            sql_queue.close_pool()
            mcs._sql_queue_cache.clear()


class SQLQueue(BaseSQLQueue, metaclass=CatchSQLQueue):
    SQL_POOLSIZE = 10

    """
    Creates a SQLQueue pool that is cached for SQLEngine instance clases
    """

    def __init__(self, queue_id=sum(map(ord, str(os.urandom(100)))), pool_size=SQL_POOLSIZE):
        super().__init__(queue_id, pool_size)
