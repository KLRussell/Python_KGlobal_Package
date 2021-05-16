from csv import reader
from portalocker import Lock
from pandas import DataFrame


class CSVReader(FileHandler):
    def __init__(self, file_path, dialect=None, **fmtparams):
        super().__init__(file_path=file_path, dialect=dialect, **fmtparams)

    def parse(self):
        if self.streams:
            for handler, buffer in self.streams:
                self.__parse(handler=handler, buffer=buffer)
        else:
            return self.__parse()

    def __parse(self, handler=None, buffer=None):
        data = list()
        row_num = 0

        with Lock(filename=self.file_path, mode='r') as read_obj:
            csv_reader = reader(read_obj, self.dialect, **self.kwargs)

            for line in csv_reader:
                data.append(line)

                if handler and buffer <= len(data):
                    df = self.__to_df(data)
                    handler(df, row_num - len(df) + 1, row_num)
                    data.clear()

                row_num += 1

        df = self.__to_df(data)

        if not df.empty and handler:
            handler(df, row_num - len(df) + 1, row_num)
        elif not handler:
            return df

    @staticmethod
    def __to_df(data):
        if data:
            df = DataFrame(data)
            new_header = df.iloc[0]
            df = df[1:]
            df.columns = new_header
            return df
        else:
            return DataFrame()
