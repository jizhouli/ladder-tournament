# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import wraps

import re
import slumber
from flask import current_app as app

from .api_errors import UnprocessableEntity


def get_backend_url(server):
    urls = app.config.get('BACKEND_APIS', {})
    if not urls:
        urls = {
            'zaih': app.config.get('ZAIH_BACKEND_API'),
        }
    return urls.get(server, None)


def get_backend_api(
        server='zaih', append_slash=False, **kwargs):
    api_url = get_backend_url(server)
    if not api_url:
        return
    api = slumber.API(
        api_url,
        auth=(
            app.config.get('BACKEND_CLIENT_ID'),
            app.config.get('BACKEND_CLIENT_SECRET')),
        append_slash=append_slash, **kwargs)
    return api


def response_setter(view):

    @wraps(view)
    def wrapper(*args, **kwargs):
        from flask import g
        from .utils import get_client, get_client_version
        client = get_client()
        g.client = client
        client_version = get_client_version()
        g.client_version = client_version
        return view(*args, **kwargs)
    return wrapper


class Validate(object):

    def __init__(self, args=None, json=None, data=None):
        self.args = args
        self.json = json
        self.data = data

    def __call__(self):
        self.validate_args()
        self.validate_data()
        self.validate_json()

    def validate_args(self):
        if self.args:
            self.validator(self.args)

    def validate_json(self):
        if self.json:
            self.validator(self.json)

    def validate_data(self):
        if self.data:
            self.validator(self.data)

    def validator(self, params):
        for field in params:
            _validator = self.__get_rule_handler('validate', field)
            _validator(params[field])

    def __get_rule_handler(self, domain, rule):
        methodname = '_{0}_{1}'.format(domain, rule.replace(' ', '_'))
        return getattr(self, methodname, None)

    def _validate_email(self, email):
        re_email = re.compile(r'^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$')
        if not re.match(re_email, email):
            raise UnprocessableEntity('invalid_email')

    def _validate_mobile(self, mobile):
        re_mobile = re.compile(r'^((\+86)|(86))?(1)[3|4|5|7|8|]\d{9}$')
        if not re.match(re_mobile, mobile):
            raise UnprocessableEntity('invalid_mobile')

    def _validate_image(self, image):
        from urlparse import urlparse
        up = urlparse(image)
        domains = ['hangjia.qiniudn.com', '7rylge.com2.z0.glb.qiniucdn.com']
        if up.scheme not in ['http', 'https'] or up.netloc not in domains:
            raise UnprocessableEntity('invalid_image')


def request_special_validate(view):
    '''
    检查特殊参数，例如手机号，邮箱
    需要配合swagger 使用
    加到Resource 的method_decorators 中
    method_decorators = [request_special_validate, request_validate, ..]
    '''

    @wraps(view)
    def wrapper(*args, **kwargs):
        from flask import g
        _args = getattr(g, 'args', None)
        json = getattr(g, 'json', None)
        data = getattr(g, 'data', None)
        Validate(_args, json, data)()
        resp = view(*args, **kwargs)
        return resp
    return wrapper
