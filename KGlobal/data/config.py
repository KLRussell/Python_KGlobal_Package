from __future__ import unicode_literals

from .picklemixin import PickleMixIn
from shutil import copy2
from threading import Lock

import os
import errno
import collections.abc
import pickle
import logging
import importlib.util as lib_import

log = logging.getLogger(__name__)


class BaseFileConfig(object):
    pass


class BaseKeyPtr(object):
    pass


class KeyPtr(BaseKeyPtr, PickleMixIn):
    """
    Key Pointer class for Key.ptr files
    """

    __slots__ = ('salt_key_fp', 'pepper_key_fp')

    def __init__(self, salt_key_fp, pepper_key_fp):
        if not isinstance(salt_key_fp, str):
            raise ValueError("'salt_key_fp' %r is not an str instance" % salt_key_fp)
        if not isinstance(pepper_key_fp, str):
            raise ValueError("'pepper_key_fp' %r is not an str instance" % pepper_key_fp)
        if not os.path.isfile(salt_key_fp):
            raise ValueError("'salt_key_fp' %s is not a valid filepath" % salt_key_fp)
        if not os.path.isfile(pepper_key_fp):
            raise ValueError("'pepper_key_fp' %s is not a valid filepath" % os.path.basename(pepper_key_fp))
        if not os.path.exists(salt_key_fp):
            raise ValueError("'salt_key_fp' %s does not exist" % os.path.basename(pepper_key_fp))

        self.__salt_key_fp = salt_key_fp
        self.__pepper_key_fp = pepper_key_fp

    def get_attr(self):
        """
        :return: Returns Salt & Pepper Filepath
        """

        return [self.__salt_key_fp, self.__pepper_key_fp]

    def __eq__(self, other):
        for k in self.__slots__:
            if getattr(self, k) != getattr(other, k):
                return False

        return True

    def __repr__(self):
        return self.__class__.__name__ + repr((str(hasH(self.__salt_key_fp)), str(hash(self.__pepper_key_fp))))


class FileConfig(BaseFileConfig, PickleMixIn):
    """
    File Configuration class object that is picked before writing to file
    """

    __slots__ = ('encrypted', 'buffer')

    def __init__(self, buffer, encrypted=False):
        """
        :param buffer: Dict or Bytes to be stored as an attribute
        :param encrypted: [Optional] (True/False) States whether buffer is encrypted or not
        """

        if not isinstance(buffer, (dict, bytes)):
            raise ValueError("'buffer' %r is not an dict or CryptHandle instance" % buffer)

        self.__encrypted = encrypted
        self.__buffer = buffer

    def get_attr(self):
        """
        :return: Returns Encrypted & Buffer attributes in a list
        """

        return [self.__encrypted, self.__buffer]

    def __eq__(self, other):
        for k in self.__slots__:
            if getattr(self, k) != getattr(other, k):
                return False

        return True

    def __repr__(self):
        return self.__class__.__name__ + repr((str(self.__encrypted), str(self.__buffer)))


class BaseDataConfig(collections.abc.MutableMapping):
    """
    A Collection ABC MutableMapping Dict list object that works like shelve but with additional functions & features

    - Class will store data into this list and will sync the data into a .db
    - A salt key will be stored in a .key file, which will be used to decrypt the saved .db data
    - All items in the list will be pickled before syncing into the .db file
    -
    - Class will automatically sync list to .db file upon class object deletion
    - There is also file lock on the read & write to prevent corruption
    - Additionally, write will begin in a .tmp file and later transferred to the .db before .tmp erases
    - It may be wise to backup the .db & .key files every once in a while
    """

    __salt_key = None
    __pepper_key = None
    __action_lock = None
    __marker = object()

    def __init__(self, file_dir, file_name_prefix, file_ext='db', encrypt=True):
        """
        Show me the location and I will settle file writing there!
        Make sure to specify salt key filepath else class will assume a new salt key
        It is good to keep everything encrypted!

        :param file_dir: File directory for where the .db file will be stored
        :param file_name_prefix: File name prefix you want the .db to be named
        :param file_ext: Extension name of database file
        :param encrypt: [Optional] (True/False) Whether you want class to encrypt written information in file
        """

        if not file_dir:
            raise ValueError("'file_dir' There is no value for this parameter")
        if not file_name_prefix:
            raise ValueError("'file_name_prefix' There is no value for this parameter")
        if file_name_prefix.find('.') > 0:
            raise ValueError("'file_name' There cannot be an extension")
        if not os.path.exists(file_dir):
            raise ValueError("'file_dir' Filepath does not exist")
        if file_ext.find('.') > -1:
            raise ValueError("'file_ext' %r has a . in it. Please remove" % file_ext)

        from .. import default_key_dir
        key_ptr_fp = os.path.join(default_key_dir(), "Key.dir")
        salt_key_fp = os.path.join(default_key_dir(), "Salt.key")
        pepper_key_fp = os.path.join(default_key_dir(), "Pepper.key")

        if os.path.exists(salt_key_fp) and os.path.exists(pepper_key_fp):
            self.__set_keys(salt_key_fp=salt_key_fp, pepper_key_fp=pepper_key_fp)
        elif os.path.exists(key_ptr_fp):
            self.__set_keys(key_ptr_fp=key_ptr_fp)
        else:
            raise ValueError("Salt & Pepper key setup hasn't been done. Please set that up")

        self.__config = dict()
        self.__buffer_write = None
        self.__config_fp = os.path.join(file_dir, '{0}.{1}'.format(file_name_prefix, file_ext))
        self.__config_tmp_fp = os.path.join(file_dir, '%s.tmp' % file_name_prefix)
        self.__encrypt = encrypt
        self.__change_list = dict()
        self.__action_lock = Lock()

        self.sync()

    def sync(self, no_resync=False):
        """
        Syncs class dict to .db file by reading the .db file & appending changes, adds,
         and deletes in current list to .db list. Keep in mind that this will sync and not
         overwrite. If you need to read the .db to be up to date, you will have to run this
         command.

         Only syncing, deleting class object, and clear functions have any reading/writing to
         the .db file
        """

        if self.__action_lock:
            try:
                from .cryptography import CryptHandle
            except ImportError:
                return
            finally:
                resync = False

            with self.__action_lock:
                try:
                    self.__sync_db()
                    self.__package_config()

                    if self.__buffer_write:
                        file_write_bytes(self.__config_tmp_fp, self.__buffer_write)
                        self.__buffer_write = None
                    else:
                        file_delete(self.__config_fp)
                except Exception as e:
                    log.warning("Ran into Ecode '{0}', {1}. Re-syncing config".format(type(e).__name__, str(e)))
                    resync = True
                finally:
                    if os.path.exists(self.__config_tmp_fp):
                        file_move(self.__config_tmp_fp, self.__config_fp, True)

            if not no_resync and resync:
                self.sync(True)

    def clear(self):
        """
        Will empty class dict and delete the .db file if exists
        """

        with self.__action_lock:
            file_delete(self.__config_fp)
            self.__config = dict()
            self.__change_list = dict()

    def pop(self, key, default=__marker):
        """
        Pop out a key's data within the class list. This will not affect the .db file until sync

        :param key: Key within the class list
        :param default: Default object to return if KeyError
        :return: data or object that derives from the class list
        """

        if self.__action_lock:
            try:
                val = self.__config[key]
            except KeyError:
                if default is self.__marker:
                    raise

                return default
            else:
                self.__change_list[key] = False
                del self.__config[key]
                return val

    def popitem(self):
        """
        Pops first item in class list. This will not affect the .db file until sync

        :return: (key, data/object) from the class list
        """

        if self.__action_lock:
            try:
                key = next(iter(self.__config))
            except StopIteration:
                raise KeyError from None

            val = self.__config[key]
            self.__change_list[key] = False
            del self.__config[key]
            return key, val

    def update(self, *args, **kwds):
        """
        Update class list with one or more dict objects. This will not affect the .db file until sync

        :param args: one dict object
        :param kwds: kwd objects (works like kwargs)
        """

        from _collections_abc import Mapping

        if not args:
            raise TypeError("descriptor 'update' of 'BaseDataConfig' object "
                            "needs an argument")
        if len(args) > 1:
            raise TypeError('update expected at most 1 arguments, got %d' %
                            len(args))

        if self.__action_lock:
            if args:
                other = args[0]

                if isinstance(other, Mapping):
                    for key in other:
                        self.__change_list[key] = True
                        self.__config[key] = other[key]
                elif hasattr(other, "keys"):
                    for key in other.keys():
                        self.__change_list[key] = True
                        self.__config[key] = other[key]
                else:
                    for key, value in other:
                        self.__change_list[key] = True
                        self.__config[key] = value

                for key, value in kwds.items():
                    self.__change_list[key] = True
                    self.__config[key] = value

    def setdefault(self, key, default=None):
        """
        Returns data/object from key or set key with default value. This will not affect the .db file until sync

        :param key: key within class list
        :param default:  default object/data
        :return: default or data from a key
        """

        if self.__action_lock:
            try:
                return self.__config[key]
            except KeyError:
                self.__change_list[key] = True
                self.__config[key] = default

            return default

    def setcrypt(self, key, val=None, private=False):
        """
        Creates a new CryptHandle object using DataConfig's salt key, sets object to class dict list according to key,
        and encrypts a value if specified.

        :param key: A key to assign within the class dict list
        :param val: [optional] encrypt a value into the newly created CryptHandle object
        :param private: [optional] (True/False) Makes peaking in the CryptHandle object private
        """

        if not isinstance(key, str):
            raise ValueError("'key' is not a String")

        if self.__action_lock:
            from .cryptography import CryptHandle

            self.__change_list[key] = True
            self.__config[key] = CryptHandle(alias=key, private=private)

            if val:
                self.__config[key].encrypt(val)

    def backup(self, backup_file_dir, backup_salt=False, salt_backup_file_dir=None):
        """
        Backup the .db and .key files (optional) to specific locations

        :param backup_file_dir: Backup file directory for .db & .key if salt_backup_file_dir isnt specified and
            backup_salt is True
        :param backup_salt: [Optional] (True/False) To backup .key file
        :param salt_backup_file_dir: [Optional] File directory for .key file
        """

        if not os.path.exists(os.path.dirname(backup_file_dir)):
            raise ValueError("'backup_file_dir' Directory %s does not exist" % os.path.dirname(backup_file_dir))

        if backup_salt:
            if salt_backup_file_dir:
                if not os.path.exists(os.path.dirname(salt_backup_file_dir)):
                    raise ValueError("'salt_backup_faile_dir' Directory %s does not exist"
                                     % os.path.dirname(salt_backup_file_dir))
            else:
                salt_backup_file_dir = backup_file_dir

        file_move(self.__config_fp, os.path.join(backup_file_dir, os.path.basename(self.__config_fp)))

        if backup_salt:
            file_move(self.__config_key_fp, os.path.join(salt_backup_file_dir, os.path.basename(self.__config_key_fp)))

    def keys(self):
        """
        :return: Returns list of keys from class dict
        """

        return list(self.__config.keys())

    def __set_keys(self, salt_key_fp=None, pepper_key_fp=None, key_ptr_fp=None):
        if salt_key_fp and pepper_key_fp and os.path.exists(salt_key_fp) and os.path.exists(pepper_key_fp):
            from .cryptography import SaltHandle

            salt_key = file_read_bytes(salt_key_fp)
            pepper_key = file_read_bytes(pepper_key_fp)

            if salt_key and isinstance(salt_key, bytes):
                self.__salt_key = pickle.loads(salt_key)

            if pepper_key and isinstance(pepper_key, bytes):
                self.__pepper_key = pickle.loads(pepper_key)

            if not self.__salt_key or not isinstance(self.__salt_key, SaltHandle):
                raise ValueError("Was unable to load salt key object")
            elif not self.__pepper_key or not isinstance(self.__pepper_key, SaltHandle):
                raise ValueError("Was unable to load pepper key object")
        elif key_ptr_fp and os.path.exists(key_ptr_fp):
            from .cryptography import SaltHandle

            key_ptr = file_read_bytes(key_ptr_fp)

            if key_ptr and isinstance(key_ptr, bytes):
                key_ptr_cls = pickle.loads(key_ptr)

                if key_ptr_cls and isinstance(key_ptr_cls, KeyPtr):
                    salt_key_fp, pepper_key_fp = key_ptr_cls.get_attr()
                    self.__set_keys(salt_key_fp=salt_key_fp, pepper_key_fp=pepper_key_fp)
                else:
                    raise ValueError("'key_ptr_fp' %s file does not hold the KeyPtr class"
                                     % os.path.basename(key_ptr_fp))
            else:
                raise ValueError("'key_ptr_fp' %s file does not hold a pickled object" % os.path.basename(key_ptr_fp))
        else:
            raise ValueError("No salt_key_fp & pepper_key_fp or key_ptr_fp was specified")

    def __package_config(self):
        from .cryptography import CryptHandle

        if self.__config:
            dict_byte = dict()

            for key, val in self.__config.items():
                if self.__encrypt:
                    crypt_obj = CryptHandle(salt=self.__salt_key)
                    crypt_obj.encrypt(val)
                    dict_byte[key] = crypt_obj.get_attr()[1]
                else:
                    dict_byte[key] = pickle.dumps(val)

            if self.__encrypt:
                crypt_obj = CryptHandle(salt=self.__pepper_key)
                crypt_obj.encrypt(dict_byte)
                dict_byte = crypt_obj.get_attr()[1]

            self.__buffer_write = pickle.dumps(FileConfig(dict_byte, self.__encrypt))

    def __unpackage_config(self):
        from .cryptography import CryptHandle

        buffer = file_read_bytes(self.__config_fp)

        if buffer and isinstance(buffer, bytes):
            config = pickle.loads(buffer)

            if not isinstance(config, FileConfig):
                raise Exception("'config' is not a Config instance")

            encrypt, my_dict = config.get_attr()

            if encrypt:
                crypt_obj = CryptHandle(salt=self.__pepper_key, enc_obj=my_dict)
                my_dict = crypt_obj.decrypt()

            if my_dict and isinstance(my_dict, dict):
                for key, val in my_dict.items():
                    if encrypt:
                        crypt_obj = CryptHandle(salt=self.__salt_key, enc_obj=my_dict[key])
                        my_dict[key] = crypt_obj.decrypt()
                    else:
                        my_dict[key] = pickle.loads(val)

                return my_dict

    def __sync_db(self):
        my_dict = self.__unpackage_config()

        if my_dict:
            if self.__change_list:
                for key, val in self.__change_list.items():
                    if val:
                        if key in self.__config.keys():
                            my_dict[key] = self.__config[key]
                    elif key in my_dict.keys():
                        del my_dict[key]

            self.__config = my_dict
            self.__change_list = dict()

    def __getstate__(self):
        # The lock cannot be pickled
        state = self.__dict__.copy()

        if state and '__action_lock' in state.keys():
            del state['__action_lock']

        return state

    def __setstate__(self, state):
        # Restore the lock
        self.__dict__.update(state)
        self.__action_lock = Lock()

    def __iter__(self):
        for k in self.__config.keys():
            yield k

    def __getitem__(self, key):
        if isinstance(key, str) and key in self.__config.keys():
            return self.__config[key]

    def __setitem__(self, key, value):
        if isinstance(key, str):
            self.__change_list[key] = True
            self.__config[key] = value

    def __delitem__(self, key):
        if isinstance(key, str) and key in self.__config.keys():
            self.__change_list[key] = False
            del self.__config[key]

    def __contains__(self, key):
        if isinstance(key, str):
            return key in self.__config.keys()

    def __len__(self):
        return len(self.__config)

    def __repr__(self):
        return self.__class__.__name__ + repr(str(self.__config))

    def __str__(self):
        return str(self.__config)

    __del__ = sync

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.sync()


class DataConfig(BaseDataConfig):
    def __init__(self, file_dir, file_name_prefix, file_ext='db', encrypt=True):
        BaseDataConfig.__init__(self, file_dir=file_dir, file_name_prefix=file_name_prefix, file_ext=file_ext,
                                encrypt=encrypt)


def file_read_bytes(file_path):
    """
    To read file that is written in bytes

    :param file_path: File path to read file (Can only read bytes)
    :return: data in bytes
    """
    import portalocker

    if not file_path:
        raise ValueError("'file_path' no value specified")

    if os.path.exists(file_path):
        with portalocker.Lock(file_path, 'rb') as f:
            data = f.read()

        return data


def file_write_bytes(file_path, data):
    """
       To write file in bytes for a specific data buffer

       :param file_path: File path to write file
       :param data: Bytes data (Please use pickle)
    """

    import portalocker

    if not file_path:
        raise ValueError("'file_path' no value specified")
    if not data:
        raise ValueError("'data' no value specified")
    if not os.path.exists(os.path.dirname(file_path)):
        raise ValueError("'file_path' directory cannot be found in file system")

    with portalocker.Lock(file_path, 'wb') as f:
        f.write(data)


def file_write_text(file_path, text):
    """
    To write file in text for a specific text file

    :param file_path: File path to write file
    :param text: Text data
    :return:
    """

    import portalocker

    if not file_path:
        raise ValueError("'file_path' no value specified")
    if not text:
        raise ValueError("'text' no value specified")
    if not os.path.exists(os.path.dirname(file_path)):
        raise ValueError("'file_path' directory cannot be found in file system")

    with portalocker.Lock(file_path, 'w') as f:
        f.write(text)


def file_delete(file_path):
    """
    Deletes file if exists

    :param file_path: File path of file to delete
    """
    if not file_path:
        raise ValueError("'file_path' no value specified")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as e:
            print("Error Code '{0}', {1}".format(type(e).__name__, str(e)))
            pass


def file_move(from_file_path, to_file_path, migrate=False):
    """
    Migrate/Copy a file from one path to a different path

    :param from_file_path:  From file path
    :param to_file_path: To file path
    :param migrate: [Optional] (True/False) To migrate or copy
    """

    if not from_file_path:
        raise ValueError("'from_file_path' no value specified")
    if not to_file_path:
        raise ValueError("'to_file_path' no value specified")
    if not os.path.exists(from_file_path):
        raise ValueError("'from_file_path' cannot be found in file system")
    if not os.path.exists(os.path.dirname(to_file_path)):
        raise ValueError("'to_file_path' directory cannot be found in file system")

    try:
        copy2(from_file_path, to_file_path)
    except OSError as e:
        print("Error Code '{0}', {1}".format(type(e).__name__, str(e)))
        pass

    if migrate:
        file_delete(from_file_path)
