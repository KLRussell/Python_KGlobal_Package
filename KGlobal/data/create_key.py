from __future__ import unicode_literals

import pickle
import os


def create_key(key_dir, key_fn):
    """
    Create salt or pepper the way I like it. Salty or Spicy!

    :param key_dir: Directory for where the key file will be created
    :param key_fn: File name for what the key file will be saved as
    """

    try:
        from . import file_write_bytes, SaltHandle
        path = os.path.join(key_dir, key_fn)

        if not os.path.exists(key_dir) or not os.path.exists(path):
            if not os.path.exists(key_dir):
                os.makedirs(key_dir)

            key = SaltHandle()
            file_write_bytes(path, pickle.dumps(key))
    except ImportError:
        raise
