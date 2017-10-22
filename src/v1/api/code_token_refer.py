# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from datetime import timedelta
from flask import request, g
from zaih_core.database import db
from zaih_core.api_errors import Unauthorized
from zaih_core.ztime import now
from src.settings import Config
from src.services.weixin import WXAPPAPI, WXBizDataCrypt

from src.models import WXAuthentication, Account, OAuth2Token
from . import Resource


class CodeToken(Resource):

    def post(self):
        code = g.json.get('code')
        if not code:
            raise Unauthorized('invalid_wxapp_token')
        approach = g.json.get('auth_approach', Authentication.APPROACH_DAYUP)
        appid = Config.WXAPP_APPID
        secret = Config.WXAPP_SECRET
        api = WXAPPAPI(appid=appid,
                       app_secret=secret)
        session_info = api.jscode2session(js_code=code)
        session_key = session_info.get('session_key')
        crypt = WXBizDataCrypt(appid, session_key)
        iv = g.json.get('iv')
        encrypted_data = g.json.get('encrypted_data')

        user_info = crypt.decrypt(encrypted_data, iv)
        openid = user_info.get('openId', None)
        # unionid
        union_id = user_info.get('unionId', None)
        if not union_id:
            raise Unauthorized('invalid_wxapp_token:union_id')
        if not openid:
            raise Unauthorized('invalid_wxapp_token:open')
        auth = Authentication.get_by_weixin(union_id)
        ddup_auth = Authentication.get_by_approach(approach, openid)
        if not auth and not ddup_auth:
            account = Account.create(
                nickname=user_info['nickName'],
                _avatar=user_info['avatarUrl']
            )
            db.session.add(Authentication(account_id=account.id,
                                          identity=openid,
                                          approach=approach,
                                          is_verified=True))
            db.session.add(
                Authentication(account_id=account.id,
                               identity=union_id,
                               approach=Authentication.APPROACH_WEIXIN,
                               is_verified=True))
            #fenda_account = check_unionid_get_account(union_id)
            #if fenda_account.get('is_verified'):
            #    if fenda_account.get('title'):
            #        account.update(commit=False,
            #                       title=fenda_account.get('title'))
            #    account.update(commit=False, is_verified=True)
        else:
            if not auth:
                account = Account.query.get(ddup_auth.account_id)
                db.session.add(
                    Authentication(account_id=account.id,
                                   identity=union_id,
                                   approach=Authentication.APPROACH_WEIXIN,
                                   is_verified=True))
                #fenda_account = check_unionid_get_account(union_id)
                #if fenda_account.get('is_verified'):
                #    if fenda_account.get('title'):
                #        account.update(commit=False,
                #                       title=fenda_account.get('title'))
                #    account.update(commit=False, is_verified=True)
            else:
                account = Account.query.get(auth.account_id)
                if not ddup_auth:
                    db.session.add(Authentication(account_id=account.id,
                                                  identity=openid,
                                                  approach=approach,
                                                  is_verified=True))
            if account.nickname != user_info['nickName']:
                account.update(
                    commit=False,
                    nickname=user_info['nickName']
                )
                db.session.add(account)
            s_time = now() - timedelta(days=7)
            if (account._avatar != user_info['avatarUrl']
                and account.date_updated < s_time):
                account.update(
                    commit=False,
                    _avatar=user_info['avatarUrl'],
                    date_updated=now(),
                )
                db.session.add(account)
        db.session.commit()
        token = OAuth2Token.get_or_create(approach, account_id=account.id,
                                          session_key=session_key)
        return token, 200, None
