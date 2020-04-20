from __future__ import unicode_literals

import pickle
import os


def create_salt(salt_dir, salt_fn):
    """
    Create salt the way I like it. Salty!

    :param salt_dir: Directory for where the salt key file will be created
    :param salt_fn: File name for what the salt key file will be saved as
    """

    try:
        from . import file_write_bytes, SaltHandle
        path = os.path.join(salt_dir, salt_fn)

        if not os.path.exists(salt_dir) or not os.path.exists(path):
            if not os.path.exists(salt_dir):
                os.makedirs(salt_dir)

            salt_key = SaltHandle()
            file_write_bytes(path, pickle.dumps(salt_key))
    except ImportError:
        raise
