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
        token = None
        code = g.json.get('code')
        if not code:
            raise Unauthorized('invalid_wxapp_token')

        # 调用微信接口，code换取session_key
        # 1. 获取session_key
        appid = Config.WXAPP_APPID
        secret = Config.WXAPP_SECRET
        api = WXAPPAPI(appid=appid,
                       app_secret=secret)
        session_info = api.jscode2session(js_code=code)
        session_key = session_info.get('session_key')

        # 2. 通过session_key解密用户信息
        crypt = WXBizDataCrypt(appid, session_key)
        iv = g.json.get('iv')
        encrypted_data = g.json.get('encrypted_data')
        user_info = crypt.decrypt(encrypted_data, iv)

        # 3. 获取用户信息
        openid = user_info.get('openId', None)
        unionid = user_info.get('unionId', '')

        nickname = user_info.get('nickName', '')
        gender = user_info.get('gender', '')
        city = user_info.get('city', '')
        province = user_info.get('province', '')
        country = user_info.get('country', '')
        avatar_url = user_info.get('avatarUrl', '')

        watermark = user_info.get('watermark', {})
        appid = watermark.get('appid', '')
        timestamp = watermark.get('timestamp', None)

        # 4. 判断用户信息字段有效性
        if not openid:
            raise Unauthorized('invalid_wxapp_token:open')

        # 5. 生成Account
        auth = WXAuthentication.query.filter_by(
            openid=openid,
            openid_type=WXAuthentication.OPENID_TYPE_XCX,
        ).first()

        # 第一次登录
        if not auth:
            account = Account.create(
                nickname=nickname,
                _avatar=avatar_url,
            )
            wxauth = WXAuthentication(
                account_id = account.id,
                unionid = unionid,
                openid = openid,
                openid_type = WXAuthentication.OPENID_TYPE_XCX,
            )
            db.session.add(wxauth)
        # 再次授权
        else:
            account = Account.query.get(auth.account_id)

        db.session.commit()
        token = OAuth2Token.get_or_create(
            WXAuthentication.OPENID_TYPE_XCX,
            account_id=account.id,
            session_key=session_key,
        )

        return token, 200, None
