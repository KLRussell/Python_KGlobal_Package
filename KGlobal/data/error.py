from __future__ import unicode_literals
from six import text_type


class GError(Exception):
    def __init__(self, value):
        super(GError, self).__init__(value)
        self.value = value

    def __str__(self):
        return text_type(self.value)


class TransportError(GError):
    pass
