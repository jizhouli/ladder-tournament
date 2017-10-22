# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from flask import Flask, render_template
from werkzeug.utils import import_string

from zaih_core.database import db, migrate

from src.settings import Config

import models

blueprints = [
]


def create_app(register_bp=True, test=False):
    app = Flask(__name__, static_folder='static')
    if test:
        app.config['TESTING'] = True
    app.config.from_object(Config)
    if register_bp:
        register_blueprints(app)
    register_extensions(app)
    register_before_request(app)
    return app


def register_extensions(app):
    db.init_app(app)
    db.app = app
    migrate.init_app(app, db)


def register_blueprints(app):
    for bp in blueprints:
        app.register_blueprint(import_string(bp))
    import v1#, panel, backend
    app.register_blueprint(v1.bp, url_prefix='/v1')
    #app.register_blueprint(panel.bp, url_prefix='/panel')
    #app.register_blueprint(backend.bp, url_prefix='/backend')


def register_before_request(app):

    def get_request_ip():
        from flask import g, request
        g.ip = request.headers.get('x-forwarded-for') or request.remote_addr

    app.before_request(get_request_ip)
