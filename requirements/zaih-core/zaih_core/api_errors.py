# -*- coding: utf-8 -*-
from __future__ import unicode_literals

'''Helper utilities and decorators.'''

from werkzeug.exceptions import HTTPException


# https://github.com/flask-restful/flask-restful/blob/7538b00b2d9b33dd2d88340e740681eafd9d056a/flask_restful/__init__.py#L272


class JSONError(HTTPException):

    code = None

    def __init__(self, error_code, message=None, text=None, errors=None):
        super(JSONError, self).__init__(message, None)
        from .error_codes import error_codes
        self.status = self.code
        self.error_code = error_code
        _message, _text = error_codes.get(error_code, (None, None))
        self.message = message or _message
        self.text = text or _text
        self.errors = errors
        self.data = self.get_response()

    def get_response(self):
        data = {
            'error_code': self.error_code,
            'message': self.message,
            'text': self.text,
            'errors': self.errors
        }
        return data


class BadRequest(JSONError):
    """
    400 Bad Request
    Raise if the browser sends something to the application the application
    or server cannot handle.
    """
    code = 400


class Unauthorized(JSONError):
    """
    401 Unauthorized
    Raise if the user is not authorized.  Also used if you want to use HTTP
    basic auth.
    """
    code = 401


class Forbidden(JSONError):
    """
    403 Forbidden
    Raise if the user doesn't have the permission for the requested resource
    but was authenticated.
    """
    code = 403


class NotFound(JSONError):
    """
    404 Not Found
    Raise if a resource does not exist and never existed.
    """
    code = 404


class MethodNotAllowed(JSONError):
    """
    405 Method Not Allowed
    Raise if the server used a method the resource does not handle.  For
    example `POST` if the resource is view only.  Especially useful for REST.
    The first argument for this exception should be a list of allowed methods.
    Strictly speaking the response would be invalid if you don't provide valid
    methods in the header which you can do with that list.
    """
    code = 405


class UnprocessableEntity(JSONError):

    """
    422 Unprocessable Entity
    Used if the request is well formed, but the instructions are otherwise
    incorrect.
    """
    code = 422


class InternalServerError(JSONError):
    """
    500 Internal Server Error
    Raise if an internal server error occurred.  This is a good fallback if an
    unknown error occurred in the dispatcher.
    """
    code = 500


class ConnectTimeoutError(JSONError):
    """
    504 Timeout
    The server was acting as a gateway or proxy and did not receive a timely
    response from the upstream server.[]
    """
    code = 504
