# -*- coding: utf-8 -*-

###
### DO NOT CHANGE THIS FILE
### 
### The code is auto generated, your change will be overwritten by 
### code generating.
###
from __future__ import absolute_import

from .api.code_token import CodeToken
from .api.hello import Hello


routes = [
    dict(resource=CodeToken, urls=['/code/token'], endpoint='code_token'),
    dict(resource=Hello, urls=['/hello'], endpoint='hello'),
]