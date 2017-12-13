__doc__ = """This is the resolver to find users using a HTTP webhook.

"""

import logging
import requests
import datetime

from UserIdResolver import UserIdResolver

log = logging.getLogger(__name__)

class HTTPCache:
    def __init__(self):
        self.values = {}
        self.timestamps = []

    def insert(self, key, value):
        now = datetime.datetime.now()
        self.values[key] = value
        self.timestamps.append((now, key))

    def lookup(self, key, default=None):
        return self.values.get(key, default)

    def bust_expired(self, td):
        now = datetime.datetime.now()
        i = 0
        for (ts, key) in self.timestamps:
            if now - ts > td:
                i = i + 1
                del self.values[key]
            else:
                break
        self.timestamps = self.timestamps[i:]


class IdResolver (UserIdResolver):

    updateable = False

    @staticmethod
    def setup(config=None, cache_dir=None):
        log.info("Setting up the HTTPIdResolver")

    def __init__(self):
        self.resolver_id = ""
        self.cache = HTTPCache()
        self.cache_expiry = datetime.timedelta(seconds=10)

    def checkPass(self, user_id, password):
        return False

    def getUserInfo(self, userid_or_username):
        """
        This function returns all user info for a given userid/object.

        :param userid_or_username: The userid or username of the object
        :type userid_or_username: string
        :return: A dictionary with the keys defined in self.map
        :rtype: dict
        """

        self.cache.bust_expired(self.cache_expiry)

        url = "%s/%s" % (self.url, userid_or_username)

        userinfo = self.cache.lookup(url, {})

        if userinfo:
            r = requests.get(url, auth=(self.username, self.password))
            if r.status_code == 200:
                try:
                    userinfo = r.json()
                    self.cache.insert(url, userinfo)
                except Exception as exx:
                    log.error("Could not decode user info to json, got %s" % r.content)
            else:
                log.error("Could not fetch userinfo, status code %s" % r.status_code)

        return userinfo

    def getUsername(self, userid):
        """
        Returns the username for a given userid
        :param userid: The userid in this resolver
        :type userid: string
        :return: username
        :rtype: string
        """

        userinfo = self.getUserInfo(userId)
        return userinfo.get('username', "")

    def getUserId(self, username):
        """
        resolve the username to the userid.

        :param username: The login name from the credentials
        :type username: string
        :return: userid as found for the username
        """

        userinfo = self.getUserInfo(username)
        return userinfo.get('userid', "")

    def getUserList(self, search_dict=None):
        """
        :param searchDict: A dictionary with search parameters
        :type searchDict: dict
        :return: list of users, where each user is a dictionary

        currently limited to returning one user
        """

        users = []
        if search_dict is not None:
            username = search_dict.get("username")
            userid_or_username = search_dict.get("userid", username)

            if userid_or_username is not None:
                userinfo = self.getUserInfo(userid_or_username)
                if len(userinfo) > 0:
                    users.append(userinfo)

        return users

    def getResolverId(self):
        """
        Returns the resolver Id
        This should be an Identifier of the resolver, preferable the type
        and the name of the resolver.
        """

        return "http." + self.resolver_id

    def loadConfig(self, config):
        self.server = config.get('Server', 'localhost')
        self.port = int(config.get('Port', 8080))
        self.schema = config.get('Schema', 'http')
        self.path = config.get('Path', '/')
        self.username = config.get('Username', '')
        self.password = config.get('Password', '')
        self.resolver_id = self.server
        self.url = "%s://%s:%s%s" % (self.schema, self.server, self.port, self.path)
        return self

    @staticmethod
    def getResolverClassType():
        return 'httpresolver'

    @staticmethod
    def getResolverType():
        return IdResolver.getResolverClassType()

    @classmethod
    def getResolverClassDescriptor(cls):
        descriptor = {}
        typ = cls.getResolverType()
        descriptor['clazz'] = "useridresolver.HTTPIdResolver.IdResolver"
        descriptor['config'] = {'Server': 'string',
                                'Port': 'int',
                                'Schema': 'string',
                                'Path': 'string',
                                'Username': 'string',
                                'Password': 'string'}
        return {typ: descriptor}

    @staticmethod
    def getResolverDescriptor():
        return IdResolver.getResolverClassDescriptor()
