# -*- coding: utf-8 -*-
import hashlib
import base64
from Crypto.Cipher import AES
import json
from src.services.utils import Request


class WXAPPError(Exception):
    def __init__(self, code, description):
        self.code = code
        self.description = description

    def __str__(self):
        return '%s: %s' % (self.code, self.description)


class WXAPPAPI(object):
    # 默认https
    host = "api.weixin.qq.com"

    def __init__(self, appid=None, app_secret=None):
        self.appid = appid
        self.app_secret = app_secret

    def pre_params(self):
        return dict(secret=self.app_secret,
                    appid=self.appid)

    def jscode2session(self, js_code):
        path = '/sns/jscode2session'
        params = self.pre_params()
        params.update(js_code=js_code,
                      grant_type='authorization_code')
        response = Request.get(self.host, path, params)
        content = json.loads(response.content.decode())
        if content.get('errcode', 0):
            raise WXAPPError(content.get('errcode', 0),
                             content.get("errmsg", ""))
        return content

    def client_credential_for_access_token(self):
        path = '/cgi-bin/token'
        params = self.pre_params()
        params.update(grant_type='client_credential')
        response = Request.get(self.host, path, params)
        content = json.loads(response.content.decode())
        if content.get('errcode', 0):
            raise WXAPPError(content.get('errcode', 0),
                             content.get("errmsg", ""))
        return content

    def getwxacode(self, access_token, page_path):
        # 接口A 数量有限 A＋C 100000个
        path = '/wxa/getwxacode?access_token=%s' % access_token
        params = {
            'path': page_path,
        }
        response = Request.post(self.host, path, params)
        try:
            content = json.loads(response.content.decode())
            if content.get('errcode', 0):
                raise WXAPPError(content.get('errcode', 0),
                                 content.get("errmsg", ""))
            return content, None
        except:
            return base64.standard_b64encode(response.content), len(response.content)


    def getwxacodeunlimit(self, access_token, scene):
        # 接口B 数量无限 scene strint(32)
        path = '/wxa/getwxacodeunlimit?access_token=%s' % access_token
        params = {
            'scene': scene,
        }
        response = Request.post(self.host, path, params)
        try:
            content = json.loads(response.content.decode())
            if content.get('errcode', 0):
                raise WXAPPError(content.get('errcode', 0),
                                 content.get("errmsg", ""))
            return content, None
        except:
            return base64.standard_b64encode(response.content), len(response.content)

    def createwxaqrcode(self, access_token, page_path):
        # 接口C 数量有限 A＋C 100000个
        path = '/cgi-bin/wxaapp/createwxaqrcode?access_token=%s' % access_token
        params = {
            'path': page_path,
        }
        response = Request.post(self.host, path, params)
        try:
            content = json.loads(response.content.decode())
            if content.get('errcode', 0):
                raise WXAPPError(content.get('errcode', 0),
                                 content.get("errmsg", ""))
            return content, None
        except:
            return base64.standard_b64encode(response.content), len(response.content)


class WXBizDataCrypt:
    def __init__(self, appid, session_key):
        self.app_id = appid
        self.session_key = session_key

    def decrypt(self, encryptedData, iv):
        # base64 decode
        sessionKey = base64.b64decode(self.session_key)
        encryptedData = base64.b64decode(encryptedData)
        iv = base64.b64decode(iv)

        cipher = AES.new(sessionKey, AES.MODE_CBC, iv)

        decrypted = json.loads(self._unpad(cipher.decrypt(encryptedData)))

        if decrypted['watermark']['appid'] != self.app_id:
            raise Exception('Invalid Buffer')

        return decrypted

    def check_raw_data(self, raw_data, session_key, signature):
        return hashlib.sha1(raw_data + session_key).hexdigest() == signature

    def _unpad(self, s):
        return s[:-ord(s[len(s) - 1:])]
