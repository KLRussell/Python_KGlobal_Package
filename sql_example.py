from KGlobal import Toolbox
from KGlobal.sql.cursor import SQLCursor
# from pandas import DataFrame

import sys

if getattr(sys, 'frozen', False):
    application_path = sys.executable
else:
    application_path = __file__


if __name__ == '__main__':
    tool = Toolbox(application_path)
    sql = tool.default_sql_conn()

    if sql:
        sql.sql_tables(queue_cursor=True)
        sql.sql_execute('SELECT * FROM schema.table', queue_cursor=True)
        sql.sql_execute('SELECT * FROM schema.table', queue_cursor=True)
        '''
        df = DataFrame()
        sql.sql_upload(dataframe=df, table_name='', table_schema='', index=False,
                       queue_cursor=True)
        '''
        results = sql.wait_for_cursors()

        if len(results) > 0:
            for result in results:
                if isinstance(result, SQLCursor):
                    print(result.is_pending)
                    print(result.cursor_action)
                    print(result.errors)
                    print(result.results)
