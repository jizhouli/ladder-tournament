# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from flask import request, g

from . import Resource
from .. import schemas


class Hello(Resource):

    def get(self):
        hello = "Hello, Ladder Tournament!"

        return hello, 200, None
