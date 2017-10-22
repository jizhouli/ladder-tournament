# -*- coding: utf-8 -*-
import sys
import requests
from requests.exceptions import (ConnectTimeout, ReadTimeout,
                                 ConnectionError)
from urllib import urlencode

TIMEOUT = 2

PY2 = sys.version_info[0] == 2
if PY2:
    text_type = unicode
    iteritems = lambda d, *args, **kwargs: d.iteritems(*args, **kwargs)

    def to_native(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None or isinstance(x, str):
            return x
        return x.encode(charset, errors)
else:
    text_type = str
    iteritems = lambda d, *args, **kwargs: iter(d.items(*args, **kwargs))

    def to_native(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None or isinstance(x, str):
            return x
        return x.decode(charset, errors)


class Request(object):
    @classmethod
    def get(cls, host, path, params, protocal='https', timeout=TIMEOUT,
            headers=None):
        uri = '%s://%s%s' % (protocal, host, path)
        str_parmas = {}
        if params:
            for k, v in params.iteritems():
                str_parmas[k] = text_type(v).encode('utf-8')
            url_params = urlencode(str_parmas)
            if url_params:
                uri = "%s?%s" % (uri, url_params)
        try:
            response = requests.get(uri, params, timeout=timeout,
                                    headers=headers)
        except (ConnectTimeout, ReadTimeout):
            raise ConnectionError('conntect_error '
                                  'Failed to establish a new connection')
        return response

    @classmethod
    def post(cls, host, path, params, protocal='https', timeout=TIMEOUT,
             headers=None):
        uri = '%s://%s%s' % (protocal, host, path)
        str_parmas = {}
        if params:
            for k, v in params.iteritems():
                str_parmas[k] = text_type(v).encode('utf-8')
        try:
            response = requests.post(uri, json=str_parmas, timeout=timeout,
                                     headers=headers)
        except (ConnectTimeout, ReadTimeout):
            raise ConnectionError('conntect_error '
                                  'Failed to establish a new connection')
        return response

    @classmethod
    def post_by_body(cls, host, path, body, protocal='https', timeout=TIMEOUT,
                     headers=None):
        uri = '%s://%s%s' % (protocal, host, path)
        try:
            response = requests.post(uri, data=body, timeout=timeout,
                                     headers=headers)
        except (ConnectTimeout, ReadTimeout):
            raise ConnectionError('conntect_error '
                                  'Failed to establish a new connection')
        return response