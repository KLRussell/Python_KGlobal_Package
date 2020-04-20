from __future__ import unicode_literals

from .data.picklemixin import PickleMixIn


class BaseCredentials(object):
    pass


class Credentials(BaseCredentials, PickleMixIn):
    """
    Base for credential storage.
    """
    __slots__ = ('class_name', 'class_id')

    def __init__(self, user_name=None, user_pass=None):
        """
        Keeps login info safe, the way that it should be!

        :param user_name: Usernames stored in an CryptHandle class object
        :param user_pass: Passwords stored in an CryptHandle class object
        """

        from .data.cryptography import CryptHandle

        if not isinstance(user_name, CryptHandle):
            raise ValueError("'username' %r must be a CryptHandle instance" % user_name)
        if not isinstance(user_pass, CryptHandle):
            raise ValueError("'password' %r must be a CryptHandle instance" % user_pass)
        if not user_name.encrypted_obj:
            raise ValueError("'user_name' does not have an encrypted object")
        if not user_pass.encrypted_obj:
            raise ValueError("'user_pass' does not have an encrypted object")

        self.__user_name = user_name
        self.__user_pass = user_pass
        self.__user_pass.private = True
        self.class_name = self.__user_name.peak()
        self.class_id = self.__user_pass.encrypted_obj

    @property
    def username(self):
        """
        :return: Returns username CryptHandle object
        """

        return self.__user_name

    @username.setter
    def username(self, username):
        """
        Sets new CryptHandle username object to class

        :param username: New username CryptHandle object
        """
        from .data.cryptography import CryptHandle

        if not isinstance(username, CryptHandle):
            raise ValueError("'username' %r must be a CryptHandle instance" % username)
        if not username.encrypted_obj:
            raise ValueError("'username' does not have an encrypted object")

        self.__user_name = username
        self.class_name = self.__user_name.peak()

    @property
    def password(self):
        """
        :return: Returns password CryptHandle object
        """

        return self.__user_pass

    @password.setter
    def password(self, password):
        """
        Sets new CryptHandle password object to class

        :param password: New password CryptHandle object
        """

        from .data.cryptography import CryptHandle

        if not isinstance(password, CryptHandle):
            raise ValueError("'password' %r must be a CryptHandle instance" % password)
        if not password.encrypted_obj:
            raise ValueError("'password' does not have an encrypted object")

        self.__user_pass = password
        self.__user_pass.private = True
        self.class_id = self.__user_pass.encrypted_obj

    def __eq__(self, other):
        for k in self.__slots__:
            if getattr(self, k) != getattr(other, k):
                return False

        return True

    def __hash__(self):
        return [hash(self.class_name), hash(self.class_id)]

    def __repr__(self):
        return self.__class__.__name__ + repr((str(self.class_name), str(self.class_id)))

    def __str__(self):
        return str(hash(self.class_name))
