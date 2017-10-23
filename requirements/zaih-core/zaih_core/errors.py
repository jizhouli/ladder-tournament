# -*- coding: utf-8 -*-
from __future__ import unicode_literals

'''Helper utilities and decorators.'''

from flask import render_template
from werkzeug.exceptions import (HTTPException as _HTTPException,
                                 BadRequest as _BadRequest,
                                 Unauthorized as _Unauthorized,
                                 Forbidden as _Forbidden,
                                 NotFound as _NotFound,
                                 InternalServerError as _InternalServerError,
                                 MethodNotAllowed as _MethodNotAllowed)


class ZaihException(Exception):
    pass


class HTTPException(ZaihException, _HTTPException):
    """封装原有方法, 实现自定义模板"""

    def get_body(self, environ):
        """Get the HTML body."""
        return render_template('errors.html', error=self)


class BadRequest(HTTPException, _BadRequest):
    pass


class Unauthorized(HTTPException, _Unauthorized):
    pass


class Forbidden(HTTPException, _Forbidden):
    pass


class NotFound(HTTPException, _NotFound):
    pass


class InternalServerError(HTTPException, _InternalServerError):
    pass


class MethodNotAllowed(HTTPException, _MethodNotAllowed):
    pass
