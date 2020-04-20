from KGlobal import Toolbox

import sys

if getattr(sys, 'frozen', False):
    application_path = sys.executable
else:
    application_path = __file__


if __name__ == '__main__':
    tool = Toolbox(application_path)
    exch = tool.default_exchange_conn()

    if exch:
        for folder in exch.root.walk():
            print(folder)

        '''
        Please use ExchangeLib website to know what commands to use. I have added renew_session() command which
        refreshes the connection if necessary.
        
            https://pypi.org/project/exchangelib/
        '''
