# -*- coding: utf-8 -*-
from __future__ import unicode_literals

try:
    import cPickle as pickle
except ImportError:
    import pickle
import time
from functools import wraps

from flask import g
from pymemcache.client.hash import HashClient

from mock_memcache import MockMemcache


def format_memcached_servers(memcached_urls):
    servers = []
    urls = memcached_urls.split(',')
    for url in urls:
        server = url.split(':')
        if not server or len(server) != 2:
            break
        host, port = server
        servers.append((host, int(port)))
    return servers


def cache_for(duration, with_uid=False):
    def deco(func):
        @wraps(func)
        def fn(*args, **kwargs):
            all_args = []
            if with_uid:
                from tutor.apis.helpers import current_user
                if current_user.is_authenticated():
                    all_args.append(current_user.id)
            all_args.append(args)
            key = pickle.dumps((all_args, kwargs))
            value, expire = func.func_dict.get(key, (None, None))
            now = int(time.time())
            if value is not None and expire > now:
                return value
            value = func(*args, **kwargs)
            func.func_dict[key] = (value, int(time.time()) + duration)
            return value
        return fn
    return deco


class CacheMeta(object):

    meta_name = None
    meta_ids = None

    def __init__(self, ids=None, obj_type='int', field_name='id',
                 is_refresh=False):
        """
        将指定用户预加载到 model_meta 缓存

        支持三种形式 ids 传递

        a. plain int: [12345678, 387474983, ...]
        b. plain string: ['12345678', '387474983', ...]
        c. object attr: [object(id=283749479), object(order_id='9437845937'), .]
        d. dict key: [{'id': 1893873494}, {'id': 9374923792}, ...]

        :Parameters
            - ids model id 列表或者含有id 的对象列表
            - field_name 含有id 的对象/字典中，id 对应的字段名
        """

        self.ids = ids
        self.field_name = field_name
        self.is_refresh = is_refresh

    def _get_ids_set(self):
        if self.ids is None:
            self.ids = []

        meta_ids = getattr(g, self.meta_ids, [])
        if meta_ids:
            self.ids = self.ids + list(meta_ids)
        ids_set = set([])
        for id in self.ids:
            if id is None:
                continue
            if isinstance(id, (int, str, long, unicode)):
                ids_set.add(id)
            else:
                try:
                    ids_set.add(getattr(id, self.field_name))
                except AttributeError:
                    ids_set.add(id[self.field_name])
        return ids_set

    def preload_meta(self):
        ids_set = self._get_ids_set()

        if not ids_set:
            return ''

        try:
            metas = self._get_metadata(*ids_set)
        except:
            raise
        else:
            setattr(g, self.meta_ids, set([]))

        try:
            _metas = getattr(g, self.meta_name, {})
            _metas.update(metas)
            setattr(g, self.meta_name, _metas)
        except AttributeError:
            setattr(g, self.meta_name, metas)
        return ''

    def _meta_values(self, id):
        if (not hasattr(g, self.meta_name) or
                id not in getattr(g, self.meta_name)):
            self.preload_meta()

        try:
            return getattr(g, self.meta_name)[id]
        except (TypeError, KeyError, AttributeError):
            return {}


class Memcache(object):

    def __init__(self, app=None, strict=False):
        self._memc_client = None

        if app is not None:
            self.init_app(app, strict)

    def local_memc(self, app):
        servers = format_memcached_servers(app.config['MEMCACHED_URLS'])
        memc = HashClient(servers, timeout=1)
        return memc

    def init_app(self, app, strict=False):
        if app.config.get('TESTING', None):
            self._memc_client = MockMemcache()
        else:
            self._memc_client = self.local_memc(app)

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['memc'] = self

    def __getattr__(self, name):
        return getattr(self._memc_client, name)


__all__ = [Memcache, cache_for, CacheMeta]
