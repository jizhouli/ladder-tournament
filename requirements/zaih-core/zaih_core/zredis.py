# -coding: utf-8 -*-
from __future__ import unicode_literals

import copy
import random

import redis
from redis import Redis
from redis.sentinel import Sentinel
from mockredis import mock_strict_redis_client


READ_COMMANDS = frozenset([
    'info', 'smembers', 'hlen', 'hmget', 'srandmember', 'hvals', 'randomkey',
    'strlen', 'dbsize', 'keys', 'ttl', 'lindex', 'type', 'llen', 'dump',
    'scard', 'echo', 'lrange', 'zcount', 'exists', 'sdiff', 'zrange', 'mget',
    'zrank', 'get', 'getbit', 'getrange', 'zrevrange', 'zrevrangebyscore',
    'hexists', 'object', 'sinter', 'zrevrank', 'hget',
    'zscore', 'hgetall', 'sismember'])


class ZaihRedis(object):

    def __init__(self, server, sentinel=None, slaves=None):

        '''
        slave_settings = {
            'master': {'name':'master','db':0,'host':'127.0.0.1','port':6379},
            'slaves': [
                {'host':'127.0.0.1','port':10001},
                {'host':'127.0.0.1','port':10002},
                {'host':'127.0.0.1','port':10003},
            ]
        }
        sentinel_settings = {
            "server": {'name': 'mymaster'},
            "sentinel": {"hosts": [('localhost', 26379)]}
        }
        '''
        self.connections = {}
        self.slaves = slaves
        name = server.pop('name', 'master')
        if sentinel:
            sentinel = Sentinel(
                sentinel['hosts'],
                socket_timeout=sentinel.get('socket_timeout', 1))
            self.connections[name] = SentinelRedis(sentinel, name)
        elif slaves:
            self.connections[name] = redis.StrictRedis(**server)
            for slave_config in slaves:
                slave_config['db'] = server['db']
                self.connections.setdefault('slaves', []).append(
                    redis.StrictRedis(**slave_config))

    def __getattr__(self, method):
        server = self.get_server(method)
        f = getattr(server, method)
        return f

    def get_server(self, method, master_only=False):
        if not self.slaves or master_only:
            return self.connections['master']
        if method in READ_COMMANDS and not master_only:
            connections = self.connections.get('slaves', [])
            if connections:
                return random.choice(connections)
        return self.connections['master']


class SentinelRedis(object):

    def __init__(self, sentinel, service_name):
        """
        Redis Sentinel cluster client
        from redis.sentinel import Sentinel
        sentinel = Sentinel([('localhost', 26379)], socket_timeout=0.1)
        master = sentinel.master_for('mymaster', socket_timeout=0.1)
        master.set('foo', 'bar')
        slave = sentinel.slave_for('mymaster', socket_timeout=0.1)
        slave.get('foo')
        'bar'
        https://github.com/andymccurdy/redis-py/blob/master/redis/sentinel.py
        """
        self.master = sentinel.master_for('master', redis_class=Redis)
        self.slave = sentinel.slave_for('slave', redis_class=Redis)

    def __getattr__(self, method):
        if method in READ_COMMANDS:
            return getattr(self.slave, method)
        else:
            return getattr(self.master, method)


class ZRedis(object):
    def __init__(self, app=None, strict=False, db=None,
                 master_server=None, slaves_server=None):
        self._redis_client = None
        self.db = db
        self.master_server = master_server
        self.slaves_server = slaves_server

        if app is not None:
            self.init_app(app, strict)

    def local_redis(self, app):
        server_config = self.master_server or copy.deepcopy(
            app.config['REDIS_MASTER_SERVER'])
        slaves_config = self.slaves_server or copy.deepcopy(
            app.config['REDIS_SLAVES_SERVER'])
        if self.db:
            server_config['db'] = self.db
        redis = ZaihRedis(server_config, slaves=slaves_config)
        return redis

    def init_app(self, app, strict=False):
        if app.config.get('TESTING', None):
            self._redis_client = mock_strict_redis_client()
        else:
            self._redis_client = self.local_redis(app)

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['redis'] = self

    def __getattr__(self, name):
        return getattr(self._redis_client, name)


__all__ = [ZRedis, ZaihRedis, SentinelRedis]
