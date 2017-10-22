# -*- coding: utf-8 -*-
from __future__ import absolute_import

from flask import Blueprint, request, g
import flask_restful as restful

from .routes import routes
from .validators import security

# verify token
from src.services.verification import verify_token, verify_request
from src.models import Account


@security.scopes_loader
def current_scopes():
    import sys
    print sys._getframe().f_code.co_filename, sys._getframe().f_code.co_name

    valid, token_info = verify_request()
    print "valid:", valid, "token:", token_info
    if valid and token_info:
        if isinstance(token_info, list):
            #scopes = set(token_info) - set(['open'])
            scopes = set(token_info)
            return list(scopes)

        account = Account.query.get(token_info.get('account_id'))
        g.account = account
        return token_info.get('scopes', [])

    return []

    #default_scopes = [] #['open', 'panel']
    #auth = request.headers.get('Authorization')
    #setattr(g, 'account_id', None)
    #if auth and auth.startswith('Bearer '):
    #    token = auth.split(' ')[-1]
    #    ret, token_info = verify_token(token)
    #    if not ret:
    #        return default_scopes
    #    account_id = token_info.get('account_id', -1)
    #    scopes = token_info.get('scopes', [])
    #    print "account_id:", account_id, "scopes:", scopes

    #    setattr(g, 'account_id', account_id)
    #    return scopes

    #return default_scopes

bp = Blueprint('v1', __name__, static_folder='static')
api = restful.Api(bp, catch_all_404s=True)

for route in routes:
    api.add_resource(route.pop('resource'), *route.pop('urls'), **route)
