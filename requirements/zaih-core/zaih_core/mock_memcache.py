# coding: utf-8

from mockredis import MockRedis
import six


class MockMemcache(MockRedis):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__()

    def set(self, key, value, expire=0, noreply=None):
        MockRedis.set(self, key, value, expire)
        return True

    def set_many(self, values, expire=0, noreply=None):
        for key, value in six.iteritems(values):
            self.set(key, value, expire, noreply)
        return True

    def add(self, key, value, expire=0, noreply=None):
        if self.get(key):
            return False
        else:
            return self.set(key, value, expire)


    def replace(self, key, value, expire=0, noreply=None):
        if self.get(key):
            return self.set(key, value, expire)
        else:
            return False

    def append(self, key, value, expire=0, noreply=None):
        v = self.get(key)
        return self.set(self, '%s %s' % (v, value), expire)

    def prepend(self, key, value, expire=0, noreply=None):
        v = self.get(key)
        return self.set(self, '%s %s' % (value, v), expire)

    def get(self, key):
        return MockRedis.get(self, key)

    def get_many(self, keys):
        return {key : self.get(key) for key in keys}

    get_multi = get_many


    #考虑重新实现
    def gets(self, key):
        return MockRedis.get(self, key), hash(key) % 100

    #重新实现
    def cas(self, key, value, cas, expire=0, noreply=False):
        return self.set(key, value, expire)

    def gets_many(self, keys):
        return [self.gets(key) for key in keys]

    def delete(self, key, noreply=None):
        MockRedis.delete(self, key)
        return True

    def delete_many(self, keys, noreply=None):
        MockRedis.delete(self, *keys)
        return True

    def incr(self, key, value, noreply=False):
        return MockRedis.incr(self, key, value)

    def decr(self, key, value, noreply=False):
        return MockRedis.decr(self, key, value)

    delete_multi = delete_many

    set_multi = set_many
