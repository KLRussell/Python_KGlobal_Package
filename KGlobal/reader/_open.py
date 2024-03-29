from ..filehandler import FileHandler
from portalocker import Lock
from ..util import DEFAULT_TIMEOUT, DEFAULT_CHECK_INTERVAL, DEFAULT_FAIL_WHEN_LOCKED, LOCK_METHOD


class OpenReader(FileHandler):
    def __init__(self, file_path, mode='a', timeout=DEFAULT_TIMEOUT, check_interval=DEFAULT_CHECK_INTERVAL,
                 fail_when_locked=DEFAULT_FAIL_WHEN_LOCKED, flags=LOCK_METHOD, **file_open_kwargs):
        super().__init__(file_path=file_path, mode=mode, timeout=timeout, check_interval=check_interval,
                         fail_when_locked=fail_when_locked, flags=flags, **file_open_kwargs)

    def parse(self):
        if self.streams:
            for handler, buffer in self.streams:
                self.__parse(handler=handler, buffer=buffer)
        else:
            return Lock(filename=self.file_path, mode=self.mode, timeout=self.timeout,
                        check_interval=self.check_interval, fail_when_locked=self.fail_when_locked, flags=self.flags,
                        **self.kwargs)

    def __parse(self, handler, buffer):
        data = list()
        row_num = 0
        header = None

        with Lock(filename=self.file_path, mode=self.mode, timeout=self.timeout, check_interval=self.check_interval,
                  fail_when_locked=self.fail_when_locked, flags=self.flags, **self.kwargs) as lines:
            for line in lines:
                data.append(line)

                if not header:
                    header = converted_row

                if buffer <= len(data):
                    handler(self.file_path, data, row_num - len(data) + 1, row_num)
                    data.clear()
                    data.append(header)

                row_num += 1

        if data:
            row_num -= 1
            handler(self.file_path, data, row_num - len(data) + 1, row_num)
        else:
            return data
