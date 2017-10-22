# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os import path, environ
from urlparse import urlparse

from .error_codes import error_codes


class EnvConfigType(type):

    def __getattribute__(cls, key):
        value = object.__getattribute__(cls, key)
        env = environ.get(key)

        if env is not None:
            value = type(value)(env)
        return value


class Config(object):

    __metaclass__ = EnvConfigType

    DEBUG = True
    TESTING = False

    DEFAULT_BASIC_TOKEN = 'YjU4ZTIwZTZiMmFmNzdjODdjZDgx'

    SECRET_KEY = '53a01e6bd34caef997eed24f5ee9d3e0'
    SQLALCHEMY_DATABASE_URI = 'postgresql://%s:%s@%s:%s/%s' % (
        environ.get('PG_USER', 'zaihang'),
        environ.get('PG_PASSWORD', 'zzzz'),
        environ.get('POSTGRES_PORT_5432_TCP_ADDR', '10.0.80.13'),
        environ.get('POSTGRES_PORT_5432_TCP_PORT', '5432'),
        environ.get('PG_DATABASE', 'lt'))

    STATIC_FOLDER = 'static'

    # 小程序配置
    WXAPP_APPID = environ.get('WXAPP_APPID', 'wx84cc28b4c3d0d695')
    WXAPP_SECRET = environ.get('WXAPP_SECRET', 'dfbc685afc267d57141c5b7b409865a1')

    # 用来app之间走backend接口校验身份，暂时未使用
    APP_CLIENT_ID = 'board'
    APP_CLIENT_SECRET = 'YhGF19NB8fgg700AVEWolGuH008N'
    # fenda认证链接
    FENDA_SERVER_HOST = environ.get('FENDA_SERVER_HOST', 'http://zhifubao:8888')
    FENDA_OAUTH_API = '{host}/backend/oauth/tokeninfo'.format(host=FENDA_SERVER_HOST)

    # APP启动类型
    APP_TYPE = environ.get('APP_TYPE', 'gpay')
    CONTAINER_TYPE = environ.get('CONTAINER_TYPE', 'gpay')
    # IAP配置
    IAP_RECEIPT_VERIFY_ALLOW_SANDBOX = environ.get('IAP_RECEIPT_VERIFY_ALLOW_SANDBOX', 'no').lower()

    # 错误码配置
    ERROR_CODES = error_codes

    # IAP付费凭证验证地址
    IAP_VERIFY_ENDPOINT_SANDBOX = 'https://sandbox.itunes.apple.com/verifyReceipt'
    IAP_VERIFY_ENDPOINT_BUY = 'https://buy.itunes.apple.com/verifyReceipt'

    # 1元人民币对分答币汇率
    IAP_EXCHANGE_RATE = 100
    # app store 分答币充值产品列表
    IAP_PRODUCT_LIST = {
        'com.fantuan.gpay_25':  17 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_50':  34 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_108': 74 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_308': 211 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_518': 355 * IAP_EXCHANGE_RATE,
    }
    # 分答币充值限额
    IAP_EXCHANGE_QUOTA_DAILY = 500 * IAP_EXCHANGE_RATE * 10000
    IAP_EXCHANGE_QUOTA_WEEKLY = 2000 * IAP_EXCHANGE_RATE * 10000

    # server info
    APP_TRANSPORT = environ.get('APP_TRANSPORT', 'http')
    APP_DOMAIN = environ.get('APP_DOMAIN', 'http://fd-iaptest.zaih.com')
    DOMAIN = '%s://%s' % (APP_TRANSPORT, urlparse(APP_DOMAIN).netloc)
    PAY_DOMAIN = environ.get('PAY_DOMAIN', '%s/py' % DOMAIN)

    GATEWAY_DOMAIN = environ.get('GATEWAY_DOMAIN', DOMAIN)
    GATEWAY_PAY_DOMAIN = environ.get('GATEWAY_PAY_DOMAIN', '%s/py' % GATEWAY_DOMAIN)

    # 微信 公众账号信息
    WEIXINMP_APPID = environ.get('WEIXINMP_APPID', 'wx28ad2c1a9f684a8e')
    WEIXINMP_APP_SECRET = environ.get('WEIXINMP_APP_SECRET',
                                      '480706fba4e1030e7419e0a7f57ffa58')

    WEIXINMP_TOKEN = environ.get('WEIXINMP_TOKEN',
                                 'OHBlcWfhMUHczZDMxNWJjMDRkZTJiOGE')
    WEIXINMP_ENCODINGAESKEY = environ.get(
        'WEIXINMP_ENCODINGAESKEY',
        '9On5TSh45id6e9RNakfPkbaElU6nZlA2ZNFe6K9fuof')

    # 微信appid 移动应用
    WEIXINAPP_APPID = environ.get('WEIXINAPP_APPID', 'wx14ebb035b39204ee')
    WEIXINAPP_APPSECRET = environ.get(
        'WEIXINAPP_APPSECRET', '11e691758f9fde0910202f642d38216a')

    # 微信支付信息
    # 微信商户号由微信统一分配的 10 位正整数 (120XXXXXXX)号
    WXPAY_MCH_ID = environ.get('WXPAY_MCH_ID', '1267441901')
    WXPAY_PARTNER_KEY = environ.get('WXPAY_PARTNER_KEY',
                                        'TN25fEepT4hcvE5IOEs9KnHus907ZWNB')

    WXAPPPAY_MCH_ID = environ.get('WXAPPPAY_MCH_ID', '1434124302')
    # 微信支付商户 Key
    WXAPPPAY_PARTNER_KEY = environ.get('WXAPPPAY_PARTNER_KEY',
                                       'a7269f5f38dc565af1987e6664bd3ef8')

    if environ.get('DEBUG'):
        WXPAY_MCH_CERT = path.normpath(path.join(
            path.dirname(__file__), 'wxpem/dev_apiclient_cert.pem'))
        WXPAY_MCH_KEY = path.normpath(path.join(
            path.dirname(__file__), 'wxpem/dev_apiclient_key.pem'))
    else:
        WXPAY_MCH_CERT = path.normpath(path.join(
            path.dirname(__file__), 'wxpem/apiclient_cert.pem'))
        WXPAY_MCH_KEY = path.normpath(path.join(
            path.dirname(__file__), 'wxpem/apiclient_key.pem'))

    # 签名方式 不需修改
    WXPAY_SIGN_TYPE = 'MD5'
    # 字符编码格式 目前支持 GBK 或 utf-8
    WXPAY_INPUT_CHARSET = 'UTF-8'
    # 交易过程中服务器通知的页面 要用
    # http://格式的完整路径，不允许加?id=123这类自定义参数
    WXPAY_NOTIFY_URL = '%s/weixin_pay/notify' % (GATEWAY_PAY_DOMAIN)
    # 微信获取用户信息接口
    WX_USER_INFO_URL = 'https://api.weixin.qq.com/cgi-bin/user/info'

    # 1元人民币对分答币汇率
    WX_EXCHANGE_RATE = 100
    # app store 分答币充值产品列表
    WX_PRODUCT_LIST = {
        'com.fantuan.gpay_test': 1,
        'com.fantuan.gpay_one': 1 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_ten': 10 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_twenty': 20 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_fifty': 50 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_onehundred': 100 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_threehundred': 300 * IAP_EXCHANGE_RATE,
        'com.fantuan.gpay_fivehundred': 500 * IAP_EXCHANGE_RATE,
    }
