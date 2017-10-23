# -*- coding: utf-8 -*-
from __future__ import unicode_literals

'''Helper utilities and decorators.'''

import re
import collections

import requests
from flask import request, current_app as app

from version import Version


def format_time(time, pfromate='%Y-%m-%d %H:%M:%S %Z%z',
                format=b'%m月%d日 %H:%M'):
    from dateutil import tz
    Beijing = tz.gettz('Asia/Shanghai')
    local_time = time.astimezone(Beijing)
    return unicode(local_time.strftime(format), 'utf-8')


def get_short_url(url):
    req = requests.post(app.config['GUO_KR_API_URL'], data={'url': url})
    if req.status_code == 201:
        short_url = req.json().get('result').get(url).get('short_url')
        return short_url[7:]
    return


def get_url_qs(url):
    from urlparse import urlparse, parse_qs
    qs = parse_qs(urlparse(url).query)
    qs = {k: ''.join(v) for k, v in qs.items()}
    return qs


def is_chinese(uchar):
    if u'\u4e00' <= uchar <= u'\u9fa5':
        return True
    return False


def is_number(uchar):
    if u'\u0030' <= uchar <= u'\u0039':
        return True
    return False


def is_alphabet(uchar):
    if (u'\u0041' <= uchar <= u'\u005a' or
            u'\u0061' <= uchar <= u'\u007a'):
        return True
    return False


def is_ip(host):
    from iptools.ipv4 import validate_ip
    return validate_ip(host)


def make_valid_unicode_str(ustr):
    valid_unicode_str = u''
    for uchar in ustr:
        if is_chinese(uchar) or is_number(uchar) or is_alphabet(uchar):
            valid_unicode_str += uchar
    return valid_unicode_str if valid_unicode_str else None


def code_generator(size=6, only_ascii=False, only_digits=False):
    import string
    import random
    chars = string.ascii_letters + string.digits
    if only_ascii:
        chars = string.ascii_uppercase
    elif only_digits:
        chars = string.digits
    code = ''.join(random.SystemRandom().choice(chars) for _ in xrange(size))
    return code


def string_to_bool(string):
    if string in ['yes', 'Yes', 'True', 'true', 't', '1']:
        return True
    elif string in ['no', 'No', 'False', 'false', 'f', '0']:
        return False
    return string


class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


def version_wrapper(version):
    if not version:
        return '0.0.0'

    version = str(version)
    main = version.split('-', 1)[0]
    items = main.split('.')
    if len(items) < 3:
        items.append('0')
    return str('-'.join(['.'.join(items)] + version.split('-', 1)[1:]))


def check_version(before=None, after=None, on=None):
    if isinstance(before, unicode):
        before = str(before)
    if isinstance(after, unicode):
        after = str(after)
    if isinstance(on, unicode):
        on = str(on)

    try:
        client_version = Version(version_wrapper(get_client_version()))
    except:
        return False

    if on and client_version != Version(version_wrapper(on)):
        return False
    if after and client_version < Version(version_wrapper(after)):
        return False
    if before and client_version > Version(version_wrapper(before)):
        return False
    return True


def get_client():
    client = 'web'
    try:
        user_agent = request.headers.get('user-agent', '')
        if user_agent.startswith('ios ') or user_agent.startswith('android '):
            client = user_agent.split()[0]
        elif user_agent.startswith('Mentor') and 'iOS' in user_agent:
            client = 'ios'
    except:
        pass
    return client


def get_client_by_browser():
    client = 'web'
    try:
        user_agent = request.user_agent.string
        is_android = user_agent.find('Android') > -1
        is_ios = bool(re.search(r'\(i[^;]+;( U;)? CPU.+Mac OS X', user_agent))
        if is_android:
            client = 'android'
        if is_ios:
            client = 'ios'
    except:
        pass
    return client


def get_client_version():
    version = '0.0.0'
    try:
        _re = re.compile(
            '(?:ios |android )?(?:zaihapp |zaihang |fenda )?'
            '(\d+)(?:\.)?(\d+)?(?:\.)?(\d+)?(?:;)?'  # minor, major, patch
            '(-[0-9A-Za-z-\.]+)?'  # pre-release
            '(\+[0-9A-Za-z-\.]+)?')  # build
        user_agent = request.headers.get('user-agent', '')
        match = _re.match(user_agent)
        if match:
            version = '.'.join(filter(None, match.groups()[:3]))
            version += ''.join(filter(None, match.groups()[3:]))
    except:
        pass
    return version


def url_params(url):
    from urlparse import urlparse, parse_qs
    return parse_qs(urlparse(url).query)


def truncate(string, length=18, end='...'):
    '''
    Return a truncated unicode copy from string or unicode
    '''
    from .coding import smart_unicode
    s = smart_unicode(string)
    if len(s) < length:
        return s
    return s[:length-len(end)] + (end if len(s) > length else '')
