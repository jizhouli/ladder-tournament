# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from functools import wraps
from flask import g
from .api_errors import Forbidden
from .helpers import get_backend_api


def get_user_resource_code(user_id):
    backend_api = get_backend_api()
    codes = backend_api.users(user_id).permissions.get()
    return codes


def check_permission(user_id, code):
    # 检查当前用户是否具有某项权限
    from flask import current_app as app
    if app.config['TESTING']:
        return True
    user_recource_code = get_user_resource_code(user_id)
    if code not in user_recource_code:
        raise Forbidden('no_permission')


def register_permission(resource_code=None):

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            # print '1' * 100
            from flask import current_app as app
            if not app.config['TESTING']:
                user_recource_code = get_user_resource_code(g.user.id)
                if resource_code:
                    if resource_code not in user_recource_code and \
                            'superman' not in user_recource_code:
                        raise Forbidden('no_permission')
            return func(*args, **kwargs)
        return wrapper

    return decorator
