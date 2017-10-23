# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import base64

import slumber
from flask import request, current_app as app
from datetime import datetime

from .caching import cache_for
from .helpers import get_backend_api


def get_authorization():
    authorization = request.headers.get('Authorization')
    if not authorization:
        return False, None
    try:
        authorization_type, token = authorization.split(' ')
        return authorization_type, token
    except ValueError:
        return False, None


def verify_token(access_token):
    # verify token return scopes
    api = slumber.API(app.config['AUTH_TOKEN_INFO_URL'],
                      auth=(app.config['APP_CLIENT_ID'],
                            app.config['APP_CLIENT_SECRET']),
                      append_slash=False)
    token_info = api.post({'access_token': access_token})
    if not isinstance(token_info, dict):
        try:
            token_info = json.loads(token_info)
        except ValueError:
            return False, None
    if (token_info.get('access_token', None) and
            datetime.utcnow() < datetime.fromtimestamp(token_info.get('expires', 0))):
            return True, token_info
    return False, None


@cache_for(3600*24)
def verify_client(token):
    if app.config['TESTING']:
        return True, ['backend']
    ALLOW_CLIENTS = app.config.get('ALLOW_CLIENTS', [])
    client = base64.b64decode(token)
    client_id, secret = client.split(':')
    if client_id not in ALLOW_CLIENTS:
        return False, None
    api = get_backend_api()
    scopes = api.client.scopes.post({'client_id': client_id, 'secret': secret})
    api = slumber.API(app.config['ZAIH_BACKEND_API'],
                      auth=(client_id, secret),
                      append_slash=False)
    scopes = api.client.scopes.get()
    if scopes:
        return True, list(set(scopes) & set(['login', 'register']))
    return False, None


def verify_request():
    authorization_type, token = get_authorization()
    if authorization_type == 'Basic':
        return verify_client(token)
    elif authorization_type == 'Bearer':
        return verify_token(token)
    return False, None
