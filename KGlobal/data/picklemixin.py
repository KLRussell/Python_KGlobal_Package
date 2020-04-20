from __future__ import unicode_literals
from future.utils import PY2


class PickleMixIn(object):
    if PY2:
        def __getstate__(self):
            return {k: getattr(self, k) for k in self.__slots__}

        def __setstate__(self, state):
            for k in self.__slots__:
                setattr(self, k, state.get(k))